from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import Author, NewsStory

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name', 'username', 'password']
        extra_kwargs = {
            'password': {'write_only': True}  # Do not include the password in the serialized output
        }
    
    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.username = validated_data.get('username', instance.username)
        password = validated_data.get('password', None)
        if password:
            instance.password = make_password(password)
        instance.save()
        return instance

class NewsStorySerializer(serializers.ModelSerializer):
    full_category = serializers.SerializerMethodField()
    full_region = serializers.SerializerMethodField()
    author_name = serializers.CharField(source='author.name', read_only=True)
    
    class Meta:
        model = NewsStory
        fields = ['id', 'headline', 'full_category', 'full_region', 'author_name', 'date', 'details']
    
    def get_full_category(self, obj):
        return dict(NewsStory.CATEGORY_CHOICES).get(obj.category, obj.category)

    def get_full_region(self, obj):
        return dict(NewsStory.REGION_CHOICES).get(obj.region, obj.region)


"""
In this implementation:

    The create method hashes the password when creating a new Author instance.
    The update method hashes the password when updating an existing Author instance, provided a new password is given.
    The password field is set as write_only to ensure it's not included in the serialized output, enhancing security.

This approach will effectively handle password hashing as part of the serialization process when creating or updating Author instances via your API.
"""