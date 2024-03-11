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
    key = serializers.IntegerField(source='id', read_only=True)
    story_cat = serializers.CharField(source='category')
    story_region = serializers.CharField(source='region')
    story_date = serializers.DateField(source='date', format="%d/%m/%Y")
    story_details = serializers.CharField(source='details')
    author = serializers.CharField(source='author.name', read_only=True)

    class Meta:
        model = NewsStory
        fields = ['key', 'headline', 'story_cat', 'story_region', 'author', 'story_date', 'story_details']

    def create(self, validated_data):
        # Extract author from the context if available
        author = self.context.get('author') if self.context else None

        # Check if author instance is provided
        if not author:
            raise serializers.ValidationError("Author is required.")

        # Remove the nested author data from validated_data
        validated_data.pop('author', None)

        # Create the NewsStory instance
        news_story = NewsStory.objects.create(author=author, **validated_data)

        return news_story

