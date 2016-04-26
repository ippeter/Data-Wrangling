import xml.etree.cElementTree as ET
import pprint as pp
import re
import codecs
import json
import os

from pymongo import MongoClient
from os.path import join, getsize

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]

problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
doublecolon = re.compile(r'.*:.*:.*')

# Let's look at  data considering Unicode. Just to see what's inside the file.
#
for _, element in ET.iterparse('.\part_of_moscow.osm'):
    for tag in element.iter('tag'):
        print('{0}: {1}'.format(tag.attrib['k'].encode('utf-8'), tag.attrib['v'].encode('utf-8')))

# Now let's count different tags that exist in the data.
#
tags = {}
for _, element in ET.iterparse('.\part_of_moscow.osm'):
    for tag in element.iter('tag'):
        key = tag.attrib['k'].encode('utf-8')
        if (key in tags):
            tags[key] = tags[key] + 1
        else:
            tags[key] = 1

pp.pprint(tags, width=1)

# Let's see one example of each tag...
#
tags = {}
for _, element in ET.iterparse('.\part_of_moscow.osm'):
    for tag in element.iter('tag'):
        key = tag.attrib['k']
        value = tag.attrib['v']
        if (not key in tags):
            tags[key] = value

for item in tags:
    print('{0}: {1}'.format(item.encode('utf-8'), tags[item].encode('utf-8')))

# Let's have a look at tags having an "address" attribute
# Output limited.
#

for _, element in ET.iterparse('.\part_of_moscow.osm'):
    temp_dict = {}
    flag = 0
    
    for tag in element.iter('tag'):
        key = tag.attrib['k']
        temp_dict[key] = tag.attrib['v']
        if (key == 'address'):
            flag = 1
    if (flag == 1):
        print('\n===New Item===\n')
        for item in temp_dict:
            print('{0}: {1}\n'.format(item.encode('utf-8'), temp_dict[item].encode('utf-8')))

# Ok, these lines sometimes have the whole address in one line:
# 
# StreetName St., h. HouseNumber, bld. BuildingNumber
# 
# I will parse these using the split_address_line() function.

# Let's look at the 'addr2' entries
#
for _, element in ET.iterparse('.\part_of_moscow.osm'):
    temp_dict = {}
    flag = 0
    for tag in element.iter('tag'):
        key = tag.attrib['k']
        temp_dict[key] = tag.attrib['v']
        if (key.startswith('addr2')):
            flag = 1
    if (flag == 1):
        print('\n===New Addr2 Item===\n')
        for item in temp_dict:
            print('{0}: {1}\n'.format(item.encode('utf-8'), temp_dict[item].encode('utf-8')))

# Let's look at the 'addr:housenumber2' entries
#
for _, element in ET.iterparse('.\part_of_moscow.osm'):
    temp_dict = {}
    flag = 0

    
    for tag in element.iter('tag'):
        key = tag.attrib['k']
        temp_dict[key] = tag.attrib['v']
        if (key == 'addr:housenumber2'):
            flag = 1
    if (flag == 1):
        print('\n===New Addr2 Item===\n')
        for item in temp_dict:
            print('{0}: {1}\n'.format(item.encode('utf-8'), temp_dict[item].encode('utf-8')))

# Okay, I understood what we have here!
# In Russia, when a house sits at the cross of two roads, it has the number of X/Y, where
# X is the house number at Road 1 and
# Y is the house number at Road 2.
# OSM users sometimes add such info by making two address entries: 
# 'addr' - Road 1 name and house number by Road 1 and 
# 'addr2' - Road 2 name and house number by Road 2.
# House numbers can still be in the X/Y format.
# I will keep this format since it's official, but I decided to create a "secondary_address" entry for addr2 and similar entries.
# 
# The same idea is sometimes implemented as addr:street2 and addr:housenumber2.
# I will take care of this case as well.

# Let's have a look at the "fuel" entries
#
for _, element in ET.iterparse('.\part_of_moscow.osm'):
    temp_dict = {}
    flag = 0

    for tag in element.iter('tag'):
        key = tag.attrib['k']
#        temp_dict[key] = tag.attrib['v']
        if (key.startswith('fuel')):
            print('{0}: {1}\n'.format(key, tag.attrib['v'].encode('utf-8')))


# Ok, it seems like this is about fuel stations.
# Let me tranform this to the following structure:
# 
# fuel:octane_95: yes
# fuel:octane_98: yes
# 
# will become
# 
# fuel: { octane_95: yes,
#         octane_98: yes}
#         
# The same logic applies for "payment" entries (example data not shown):
# 
# payment:visa: yes
# payment:mastercard: yes
# 
# will become
# 
# payment : { visa: yes,
#             mastercard: yes}

# Finally let's have a look at the "building" entries
#
for _, element in ET.iterparse('.\part_of_moscow.osm'):
    temp_dict = {}
    flag = 0
    for tag in element.iter('tag'):
        key = tag.attrib['k']
        temp_dict[key] = tag.attrib['v']
        if (key.startswith('building')):
            parts = key.split(':')
            if (len(parts) > 1):
                if (parts[1] == 'color'):
                    flag = 1
                    #pp.pprint(element, width=1)
                    #print('{0}: {1}\n'.format(key, tag.attrib['v'].encode('utf-8')))

    if (flag):
        pp.pprint(temp_dict, width=4)


# Ok, we have a complicated structure for tags that start with "building".
# I decided to go for the following transformation:
# 
# building: school,
# building:roof: concrete,
# building:roof:colour: #C7C7C7,
# building:levels: 1
# building:levels:underground: 1
# 
# will become
# 
# building: {type: school,
#             roof: {type: concrete,
#                     colour: #C7C7C7},
#             levels: {amount: 1,
#                     underground: 1}
#            }
# 
# Other k:v pairs will remain unchanged.
# 
# Also I noticed from the outputs above that there are many international options for "name", "alt_name" and "official_name" entries. Let me go for the following transformation:
# 
# name: NameInRussian
# name:en: NameInEnglish
# name:de: NameInGerman
# 
# will become
# 
# name: NameInRussian
# name_international: {en: NameInEnglish,
#                     de: NameInGerman}
#                     
# Same for "alt_name" and "official_name"
# 
# That's it. There are much, MUCH more other things that could be taken care of.
# But it will take me ages to go through them.
# Let me focus on the fixes that I selected above and implement them.
# 
# Next come functions for the transformation process.
# Note: I copied the approach for "created" and "position" from the course.

# Split Russian full address line into a tuple: (street, housenumber, building)
# Returns None if unsplittable (that is, something is wrong)
#
def split_address_line(address):
    parts = address.split(',')
    if (len(parts) == 3):
        street_name = parts[0].strip()
        house_number = re.search(r'[0-9]+', parts[1]).group()
        building_number = re.search(r'[0-9]+', parts[2]).group()
        return (street_name, house_number, building_number)
    else:
        return None

# Main function to shape map elements into JSON
#
def shape_element(element):
    node = {}
    if (element.tag == 'node') or (element.tag == 'way'):
        node['type'] = element.tag
        # Empty elements to be filled later
        temp_dict = {'created': {}, \
                     'address': {},  \
                     'secondary_address': {}, \
                     'fuel': {}, \
                     'payment': {}, \
                     'building': {}, \
                     'position': [] }
        latitude = None
        longitude = None
        
        # Handle the "created" items
        for a in element.attrib:
            if (a in CREATED):
                temp_dict['created'][a] = element.attrib[a]
            elif (a == 'lat'):
                latitude = float(element.attrib[a])
            elif (a == 'lon'):
                longitude = float(element.attrib[a])
            else:
                node[a] = element.attrib[a]
        
        if (latitude) and (longitude):
            temp_dict['position'] = [latitude, longitude]
        
        # Handle underlying tags    
        for tag in element.iter('tag'):
            key = tag.attrib['k']
            value = tag.attrib['v'].encode('utf-8')
            
            #
            # Main shaping body
            #
            if (key.startswith('addr')):
                # Handle various address items
                if (key == 'address'):
                    # Handle full address lines such as "StreetName St., h. HouseNumber, bld. BuildingNumber"
                    parts = split_address_line(value)
                    if (parts):
                        temp_dict['address']['street'] = parts[0]
                        temp_dict['address']['housenumber'] = parts[1]
                        temp_dict['address']['building'] = parts[2]
                else:
                    # Handle other address items such as "addr2:street" or "addr:street2"
                    parts = key.translate(None, '2').split(':')
                    if (len(parts) == 3):
                        # Handle addr:city:en entry
                        parts[1] = parts[1] + '_internaltional'
                    if ('2' in key):
                        # We have either "addr2:street" or "addr:street2" so we fill an secondary address
                        temp_dict['secondary_address'][parts[1]] = value
                    else:
                        # We have a primary address item
                        temp_dict['address'][parts[1]] = value
            
            elif (key.startswith('fuel')):
                # Handle fuel entries
                parts = key.split(':')
                temp_dict['fuel'][parts[1]] = value
            
            elif (key.startswith('payment')):
                # Handle payment entries
                parts = key.split(':')
                temp_dict['payment'][parts[1]] = value
            
            elif (key.startswith('building')):
                # Handle building entries
                parts = key.split(':')
                if (len(parts) == 1):
                    # Fill building type
                    if (value <> 'yes'):
                        temp_dict['building']['type'] = value
                elif (len(parts) == 2):
                    # Prepare sub-dicts for "levels", "roof" and make normal entries for others
                    if (parts[1] == 'levels') or (parts[1] == 'roof'):
                        if (parts[1] not in building):
                            temp_dict['building'][parts[1]] = {}                        
                        if (parts[1] == 'levels'):
                            temp_dict['building']['levels']['amount'] = value
                        else:
                            temp_dict['building']['roof']['type'] = value
                    else:
                        temp_dict['building'][parts[1]] = value
                else:
                    # Fill sub-dicts for "levels", "roof". Here I handle double-colon items, i.e. "building:roof:color"
                    if (parts[1] not in building):
                        temp_dict['building'][parts[1]] = {}
                    temp_dict['building'][parts[1]][parts[2]] = value
        
            elif (key.startswith('name')) or (key.startswith('alt_name')) or (key.startswith('official_name')):
                # Handle name, alt_name and official_name items
                parts = key.split(':')
                if (len(parts) > 1):
                    # We have an international entry, such as "name:en", for example
                    international_dict = parts[0] + '_international'
                    if (international_dict not in node):
                        node[international_dict] = {}
                    node[international_dict][parts[1]] = value
                else:
                    # We have normal name, alt_name and official_name items
                    node[key] = value

            else:
                # Default handler for all the rest
                # I drop all items with problematic characters and all items with double-colon
                if (re.match(problemchars, key) == None) and (re.match(doublecolon, key) == None):
                    if (key <> 'type'):
                        # There might be tags with the key of 'type' and it will interfere with the node type we set above.
                        node[key] = value
                
            # Handle nd tags for "way"
            if (element.tag == "way"):
                node['node_refs'] = []
                for tag in element.iter('nd'):
                    node['node_refs'].append(tag.attrib['ref'])
                
        # Final part. Assemble all sub-dicts together provided that they were filled
        for item in temp_dict:
            if (temp_dict[item]):
                node[item] = temp_dict[item]
        return node
    else:
        return None


# Main body for map processing
#
file_out = "{0}.json".format('part_of_moscow')

with codecs.open(file_out, "w") as fo:
    for _, element in ET.iterparse('.\part_of_moscow.osm'):
        el = shape_element(element)
        if el:
            fo.write(json.dumps(el) + "\n")


# Sizes of files I work with
#
for root, dirs, files in os.walk('.'):
    for name in files:
        if ('moscow' in name):
            print('File: {0}\t\tSize: {1} bytes'.format(name,getsize(name)))


# Ok, both files are more than 50 MB.
# 
# At this point I load my JSON file into the MongoDB instance using the following OS command:
# 
# c:\Program Files\MongoDB\Server\3.2\bin>mongoimport -d examples -c moscow --file
#  "d:\Udacity\P3 Data Wrangling with MongoDB\part_of_moscow.json"
# 2016-04-24T13:24:17.010+0300    connected to: localhost
# 2016-04-24T13:24:19.985+0300    [######..................] examples.moscow
# 23.6 MB/93.2 MB (25.3%)
# 2016-04-24T13:24:22.985+0300    [############............] examples.moscow
# 48.6 MB/93.2 MB (52.2%)
# 2016-04-24T13:24:25.985+0300    [##################......] examples.moscow
# 72.5 MB/93.2 MB (77.8%)
# 2016-04-24T13:24:28.311+0300    [########################] examples.moscow
# 93.2 MB/93.2 MB (100.0%)
# 2016-04-24T13:24:28.312+0300    imported 412257 documents
# 
# c:\Program Files\MongoDB\Server\3.2\bin>
# 
# Now let's investigate data in the database with some queries.

# Establish a connection to the database run locally
#
client = MongoClient('mongodb://localhost:27017')

db = client.examples

# Number of documents in the database:
#
number_of_documents = db.moscow.find().count()

print 'Number of Moscow documents: ', number_of_documents


# Ok, it's the same to the number of documents that were imported using mongoimport

# Number of 'node' and 'way' tags:
#
pipeline = [{ "$group" : { "_id" : "$type", \
                           "count" : { "$sum" : 1 } } }]

pp.pprint([doc for doc in db.moscow.aggregate(pipeline)], width=4)


# Number of unique contributors.
# It's definitely a dirty way, but I didn't want to copy the nice query based on "distinct" from the submission example :)
#
pipeline = [{ "$group" : { "_id" : "Unique users", \
                           "unique_users" : { "$addToSet" : "$created.user"} } }, \
            { "$project" : { "Count" : { "$size" : "$unique_users" } } }]
    
pp.pprint([doc for doc in db.moscow.aggregate(pipeline)], width=4)

# Top 10 contributing users
# Note the Unicode characters in user names!
#
pipeline = [{ "$group" : { "_id" : "$created.user", \
                           "count" : { "$sum" : 1 } } }, \
            { "$sort" : { "count" : -1 } }, \
            { "$limit" : 10 }]

result = db.moscow.aggregate(pipeline)

for doc in result:
    print('User: {0}, Contributions: {1}'.format(doc['_id'].encode('utf-8'), doc['count']))


# Let's see how many documents have a "secondary_address" info that I created while shaping
#
pipeline = [{ "$match" : { "secondary_address" : { "$exists" : 1 } } }, \
            { "$group" : { "_id" : "Documents having a secondary address", \
                           "count" : { "$sum" : 1 } } }]
 
pp.pprint([doc for doc in db.moscow.aggregate(pipeline)], width=4)

# A couple of additional queries against the database.
#
# Let's calculate different types of buildings that we have in the database
#
pipeline = [{ "$match" : { "building.type" : { "$exists" : 1 } } }, \
            { "$group" : { "_id" : "$building.type", \
                           "count" : { "$sum" : 1 } } }, \
            { "$sort" : { "count" : -1 } }]

pp.pprint([doc for doc in db.moscow.aggregate(pipeline)], width=4)


# Finally let's see how many documents have a "name_international" info that I created while shaping
# A bit more complex query than the one above...
#
pipeline = [{ "$match" : { "$or": [ \
    { "name_international" : { "$exists" : 1 } },  \
    { "alt_name_international" : { "$exists" : 1 } }, \
    { "official_name_international" : { "$exists" : 1 } }, \
    ] } }, \
            { "$group" : { "_id" : "Documents having international names",  \
                           "count" : { "$sum" : 1 } } }]
    
pp.pprint([doc for doc in db.moscow.aggregate(pipeline)], width=4)

