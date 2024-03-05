from django.db import models
from django.contrib.auth.hashers import make_password

class Author(models.Model):
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        self.password = make_password(self.password)
        super(Author, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

class NewsStory(models.Model):
    CATEGORY_CHOICES = [
        ('pol', 'Politics'),
        ('art', 'Art'),
        ('tech', 'Technology'),
        ('trivia', 'Trivia'),
    ]
    REGION_CHOICES = [
        ('uk', 'UK'),
        ('eu', 'Europe'),
        ('w', 'World'),
    ]

    headline = models.CharField(max_length=64)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    region = models.CharField(max_length=10, choices=REGION_CHOICES)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    date = models.DateField()
    details = models.CharField(max_length=128)

    def __str__(self):
        return self.headline
