from django.contrib import admin

from .models import Category, Item, ItemPhoto


class ItemPhotoInline(admin.TabularInline):
    model = ItemPhoto
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'category', 'daily_price', 'is_active')
    list_filter = ('category', 'condition', 'is_active')
    search_fields = ('title', 'owner__username')
    inlines = [ItemPhotoInline]