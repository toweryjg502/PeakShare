from django.http import Http404
from django.shortcuts import get_object_or_404, render

from .models import Category, Item


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
    return render(request, 'listings/item_detail.html', {'item': item})