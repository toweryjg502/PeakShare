from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

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
    slug = request.GET.get('category')
    if slug:
        selected_category = get_object_or_404(Category, slug=slug)
        items = items.filter(category=selected_category)
    return render(request, 'listings/item_list.html', {
        'items': items,
        'categories': Category.objects.all(),
        'selected_category': selected_category,
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
    })

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
    return render(request, 'listings/item_form.html', {'form': form})

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