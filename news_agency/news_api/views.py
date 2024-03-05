from django.shortcuts import render

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import NewsStory, Author
from .serializers import NewsStorySerializer, AuthorSerializer
from django.http import HttpResponse
from datetime import date

def root_view(request):
    return HttpResponse("Welcome to the News Agency API.")

#Log In
@api_view(['POST'])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        try:
            author = Author.objects.get(username=username)
            author_name = author.name
        except Author.DoesNotExist:
            author_name = None
        return Response({
            "username": username,
            "name": author_name  # Now you return the author's name
        }, status=status.HTTP_200_OK)
    else:
        return Response({"message": "Login failed. Please check username and password."},
                        status=status.HTTP_401_UNAUTHORIZED)

#Log Out
@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({"message": "You are now logged out."}, status=status.HTTP_200_OK)

#Post Story
@api_view(['POST'])
def post_story(request):
    if request.user.is_authenticated:
        data = request.data.copy()
        data['date'] = date.today().isoformat()

        try:
            author_instance = Author.objects.get(username=request.user.username)
        except Author.DoesNotExist:
            return Response({"message": "Author not found."},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = NewsStorySerializer(data=data)
        if serializer.is_valid():
            serializer.save(author=author_instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"message": "User not authenticated."},
                        status=status.HTTP_401_UNAUTHORIZED)


#Get Stories
@api_view(['GET'])
def get_stories(request):
    # Retrieve query parameters
    story_cat = request.query_params.get('story_cat', '*')
    story_region = request.query_params.get('story_region', '*')
    story_date = request.query_params.get('story_date', '*')

    # Apply filtering
    stories = NewsStory.objects.all()
    if story_cat != '*':
        stories = stories.filter(category=story_cat)
    if story_region != '*':
        stories = stories.filter(region=story_region)
    if story_date != '*':
        stories = stories.filter(date__gte=story_date)  # assuming story_date is a date string in 'YYYY-MM-DD' format

    serializer = NewsStorySerializer(stories, many=True)
    return Response(serializer.data)


#Delete Story
@api_view(['DELETE'])
def delete_story(request, pk):
    try:
        story = NewsStory.objects.get(pk=pk)
        if request.user.is_authenticated and story.author == request.user:
            story.delete()
            return Response({"message": "Story deleted successfully."},
                            status=status.HTTP_200_OK)
        else:
            return Response({"message": "Unauthorized to delete this story."},
                            status=status.HTTP_401_UNAUTHORIZED)
    except NewsStory.DoesNotExist:
        return Response({"message": "Story not found."},
                        status=status.HTTP_404_NOT_FOUND)
