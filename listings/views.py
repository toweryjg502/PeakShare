from django.contrib import messages
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.db.models import Q
from django.db.models import Avg
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date

from accounts.decorators import verified_required

from .forms import ItemEditForm, ItemForm
from .models import Category, Item, ItemPhoto

from bookings.availability import unavailable_ranges

def item_list(request):
    items = (
        Item.objects.filter(is_active=True)
        .select_related('category')
        .prefetch_related('photos')
    )
    selected_category = None
    query = request.GET.get('q', '').strip()
    condition = request.GET.get('condition', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    sort = request.GET.get('sort', 'newest')
    start_date = parse_date(request.GET.get('start_date', ''))
    end_date = parse_date(request.GET.get('end_date', ''))
    if query:
        items = items.filter(Q(title__icontains=query) | Q(description__icontains=query))
    slug = request.GET.get('category')
    if slug:
        selected_category = get_object_or_404(Category, slug=slug)
        items = items.filter(category=selected_category)
    if condition in dict(Item.Condition.choices):
        items = items.filter(condition=condition)
    if min_price:
        try:
            value = Decimal(min_price)
            if not value.is_finite():
                raise InvalidOperation
            items = items.filter(daily_price__gte=max(Decimal('0'), value))
        except (ValueError, InvalidOperation):
            min_price = ''
    if max_price:
        try:
            value = Decimal(max_price)
            if not value.is_finite():
                raise InvalidOperation
            items = items.filter(daily_price__lte=max(Decimal('0'), value))
        except (ValueError, InvalidOperation):
            max_price = ''
    if start_date and end_date and end_date >= start_date:
        items = items.exclude(
            bookings__status='approved', bookings__start_date__lte=end_date,
            bookings__end_date__gte=start_date,
        ).exclude(
            blackout_dates__start_date__lte=end_date,
            blackout_dates__end_date__gte=start_date,
        )
        items = items.distinct()
    sort_fields = {
        'newest': '-created_at',
        'price_low': 'daily_price',
        'price_high': '-daily_price',
        'title': 'title',
    }
    if sort not in sort_fields:
        sort = 'newest'
    items = items.order_by(sort_fields[sort], 'pk')
    active_filters = any((query, slug, condition, min_price, max_price,
                          request.GET.get('start_date', ''), request.GET.get('end_date', '')))
    return render(request, 'listings/item_list.html', {
        'items': items,
        'categories': Category.objects.all(),
        'selected_category': selected_category,
        'filters': {
            'q': query, 'condition': condition, 'min_price': min_price,
            'max_price': max_price,
            'start_date': request.GET.get('start_date', ''),
            'end_date': request.GET.get('end_date', ''),
            'sort': sort,
        },
        'conditions': Item.Condition.choices,
        'sort_options': [
            ('newest', 'Newest'), ('price_low', 'Price: low to high'),
            ('price_high', 'Price: high to low'), ('title', 'Title: A to Z'),
        ],
        'active_filters': active_filters,
    })


def item_detail(request, pk):
    item = get_object_or_404(
        Item.objects.select_related('category', 'owner').prefetch_related('photos'),
        pk=pk,
    )
    # Hidden listings are only visible to their owner
    if not item.is_active and item.owner != request.user:
        raise Http404
    return render(request, 'listings/item_detail.html', {
        'item': item,
        'unavailable': unavailable_ranges(item),
        'owner_reviews': item.owner.received_reviews.filter(
            reviewer__isnull=False
        ).select_related('reviewer', 'booking').order_by('-created_at')[:10],
        'owner_review_count': item.owner.received_reviews.count(),
    })


def price_suggestion(category, condition, instance=None):
    """Suggest a transparent category-based starting price, never auto-set it."""
    prices = Item.objects.filter(category=category, is_active=True)
    if instance and instance.pk:
        prices = prices.exclude(pk=instance.pk)
    average = prices.aggregate(value=Avg('daily_price'))['value']
    if average is None:
        return None
    multiplier = {
        Item.Condition.LIKE_NEW: 1.10,
        Item.Condition.GOOD: 1.0,
        Item.Condition.FAIR: 0.85,
    }.get(condition, 1.0)
    return (average * Decimal(str(multiplier))).quantize(Decimal('0.01'))

@verified_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                item = form.save(commit=False)
                item.owner = request.user
                item.save()
                for image in form.cleaned_data['photos']:
                    ItemPhoto.objects.create(item=item, image=image)
            return redirect('item_detail', pk=item.pk)
    else:
        form = ItemForm()
    guidance = {
        str(row['id']): str(row['average'])
        for row in Category.objects.annotate(average=Avg('items__daily_price'))
        .exclude(average__isnull=True).values('id', 'average')
    }
    return render(request, 'listings/item_form.html', {
        'form': form,
        'price_guidance': guidance,
    })

@verified_required
def item_edit(request, pk):
    # Filtering by owner means other users get a 404, not a peek at the form
    item = get_object_or_404(Item, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ItemEditForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                form.cleaned_data['remove_photos'].delete()
                for image in form.cleaned_data['new_photos']:
                    ItemPhoto.objects.create(item=item, image=image)
            messages.success(request, 'Listing updated.')
            return redirect('item_detail', pk=item.pk)
    else:
        form = ItemEditForm(instance=item)
    return render(request, 'listings/item_form.html', {
        'form': form,
        'heading': f'Edit: {item.title}',
        'submit_label': 'Save Changes',
        'suggested_price': price_suggestion(item.category, item.condition, item),
    })


@verified_required
@require_POST
def item_toggle_active(request, pk):
    item = get_object_or_404(Item, pk=pk, owner=request.user)
    item.is_active = not item.is_active
    item.save(update_fields=['is_active', 'updated_at'])
    if item.is_active:
        messages.success(request, 'Your listing is visible again.')
    else:
        messages.success(request, 'Your listing is now hidden from other users.')
    return redirect('item_detail', pk=item.pk)
