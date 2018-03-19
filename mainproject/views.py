from django.shortcuts import render

# Create your views here.

def index(request):
	return render(request, 'home.html')

def contact(request):
	return render(request, 'contact.html', {'content': ['Contact the web developer:', 'xd24 (at) duke.edu']})