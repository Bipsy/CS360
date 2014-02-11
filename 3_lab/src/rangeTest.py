import requests

custom_header = {'Range':"bytes=0-644"}
response = requests.get('http://CS360.byu.edu', stream=True, headers=custom_header)
print response.content
