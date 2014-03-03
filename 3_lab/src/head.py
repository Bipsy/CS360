import urllib

data = urllib.urlopen('http://diveintomark.org/xml/atom.xml').read()
print data

