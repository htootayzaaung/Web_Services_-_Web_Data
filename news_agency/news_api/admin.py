from django.contrib import admin
from .models import Author, NewsStory

admin.site.register(Author)

# Define a custom admin interface for NewsStory
class NewsStoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'headline', 'category', 'region', 'author', 'date', 'details')

admin.site.register(NewsStory, NewsStoryAdmin)