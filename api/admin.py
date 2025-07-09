from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'age', 'city', 'created_at')
    list_filter = ('city', 'created_at')
    search_fields = ('name', 'city')
    ordering = ('-created_at',)
