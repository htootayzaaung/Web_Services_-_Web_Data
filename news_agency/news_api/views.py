from django.shortcuts import render

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import NewsStory, Author
from .serializers import NewsStorySerializer, AuthorSerializer
from django.http import HttpResponse
import datetime
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
        return HttpResponse(f"Welcome, {author_name}!", status=status.HTTP_200_OK, content_type="text/plain")
    else:
        return HttpResponse("Login failed. Please check username and password.", status=status.HTTP_401_UNAUTHORIZED, content_type="text/plain")

#Log Out
@api_view(['POST'])
def logout_view(request):
    logout(request)
    return HttpResponse("Goodbye! You are now logged out.", status=status.HTTP_200_OK, content_type="text/plain")

#Post Story and Get Stories
@api_view(['GET', 'POST'])
def stories_view(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return HttpResponse("User not authenticated. Cannot post story.", status=status.HTTP_503_SERVICE_UNAVAILABLE, content_type="text/plain")

        data = request.data.copy()
        data.setdefault('date', date.today().isoformat())

        try:
            author_instance = Author.objects.get(username=request.user.username)
            data['author'] = author_instance.id  # Set author as the instance's ID
        except Author.DoesNotExist:
            return HttpResponse("Author not found.", status=status.HTTP_503_SERVICE_UNAVAILABLE, content_type="text/plain")

        serializer = NewsStorySerializer(data=request.data, context={'author': author_instance})
        if serializer.is_valid():
            serializer.save()
            return HttpResponse("Story posted successfully.", status=status.HTTP_201_CREATED, content_type="text/plain")
        else:
            errors = serializer.errors
            return HttpResponse("Failed to post story: " + str(errors), status=status.HTTP_503_SERVICE_UNAVAILABLE, content_type="text/plain")
    
    elif request.method == 'GET':
        story_cat = request.query_params.get('category', '*')
        story_region = request.query_params.get('region', '*')
        story_date = request.query_params.get('date', '*')

        stories = NewsStory.objects.all()

        if story_cat != '*':
            stories = stories.filter(category=story_cat)
        if story_region != '*':
            stories = stories.filter(region=story_region)
        if story_date != '*':
            try:
                parsed_date = datetime.datetime.strptime(story_date, "%d/%m/%Y").date()
                stories = stories.filter(date__gte=parsed_date)
            except ValueError:
                return HttpResponse("Invalid date format. Please enter the date in 'dd/mm/yyyy' format.", status=status.HTTP_400_BAD_REQUEST, content_type="text/plain")

        if not stories.exists():
            return HttpResponse("No stories found matching the criteria.", status=status.HTTP_404_NOT_FOUND, content_type="text/plain")

        serializer = NewsStorySerializer(stories, many=True)
        return Response({'stories': serializer.data})

@api_view(['DELETE'])
def delete_story(request, pk):
    try:
        story = NewsStory.objects.get(pk=pk)
        if request.user.is_authenticated:
            # Check if the logged-in user is the author of the story
            if story.author.username == request.user.username:
                story.delete()
                return HttpResponse("Story deleted successfully.", status=status.HTTP_200_OK, content_type="text/plain")
            else:
                return HttpResponse("Unauthorized to delete this story.", status=status.HTTP_403_FORBIDDEN, content_type="text/plain")
        else:
            return HttpResponse("User not authenticated.", status=status.HTTP_401_UNAUTHORIZED, content_type="text/plain")
    except NewsStory.DoesNotExist:
        return HttpResponse("Story not found.", status=status.HTTP_404_NOT_FOUND, content_type="text/plain")
    except Exception as e:
        # Handle any other exception
        return HttpResponse(f"An error occurred: {str(e)}", status=status.HTTP_503_SERVICE_UNAVAILABLE, content_type="text/plain")
