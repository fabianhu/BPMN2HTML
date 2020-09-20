#!/usr/bin/python3

import os
import sys
import json                             #for debug
import numpy as np
from xml.etree import ElementTree
from datetime import datetime
from contextlib import contextmanager

# BEGINN installation process
@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout

try:
    from pip import main as pipmain
except ImportError:
    from pip._internal import main as pipmain

def install(package):
    print("Try to install {} over pip".format(package))
    print(pipmain(['install', package]))

try:
    import cv2
except ModuleNotFoundError as e:
    try:
        install('opencv-python')
    except Exception as e:
            print('Can\'t install {}:{}'.format('openCV-python', e))
            raise(e)

import cv2

# END installation process

mult = 3  # fixed value to multiply xml values to get the image values
# every tag with string in it, will be painted:
tagstopaint = {'Event':'circle',
               'task':'rect',
               'Gateway':'poly',
               'dataStore':'rect',
               'dataObject':'rect',}


def enc(st):
    '''encode strings for htm'''
    st = st.replace("\"", '&quot;')
    encod = st.encode(encoding="ascii", errors="xmlcharrefreplace")
    decod = encod.decode("utf-8")
    return decod


# read xml for max size
def parse_bpmn_bounds(xmlroot, namespace):  # -> (x,y)
    '''Read the shape of the image descripted in the xml the bounds'''
    bounds = xmlroot.findall("bpmndi:BPMNDiagram/bpmndi:BPMNPlane/bpmndi:BPMNShape/dc:Bounds", namespace)
    bounds = bounds + xmlroot.findall("bpmndi:BPMNDiagram/bpmndi:BPMNPlane/bpmndi:BPMNShape/bpmndi:BPMNLabel/dc:Bounds", namespace)

    # find the outer bounds
    xmin = 30000
    xmax = -30000
    ymin = 30000
    ymax = -30000
    for i in bounds:
        rx = int(float(i.get('x'))) * mult
        ry = int(float(i.get('y'))) * mult
        rw = int(i.get('width')) * mult
        rh = int(i.get('height')) * mult
        xmin = min(rx, xmin)
        xmax = max(rx + rw, xmax)
        ymin = min(ry, ymin)
        ymax = max(ry + rh, ymax)

    # print("xml off:", xmin, ymin)
    xmlwidth = xmax - xmin
    xmlheight = ymax - ymin

    return xmlwidth, xmlheight, xmin, ymin


def build_tree(xmlroot):
    '''build the elemental tree from the xml description'''
    childrens = xmlroot.getchildren()
    cds = []
    tree = {}
    for cd in childrens:
        cds.append(build_tree(cd))
    tree['tag'] = xmlroot.tag.split('}')[1]
    if len(cds) != 0:
        j = 0
        for i in cds:
            if 'tag' in i:
                if i['tag'] == 'property' and i['name'] == 'link':
                    tree['link'] = cds.pop(j)['value']
                if i['tag'] == 'documentation':
                    tree['documentation'] = cds.pop(j)['text']
                if i['tag'] == 'properties' and 'link' in i:
                    tree['link'] = cds.pop(j)['link']
            j+=1
        j = 0
        for i in cds:
            if i['tag'] == 'extensionElements':
                if 'link' in cds[j]:
                    tree['link'] = cds.pop(j)['link']
            j+=1
        j = 0
        if len(cds) !=0:
            tree['subelements'] = cds
    text = xmlroot.text
    if text != None:
        tree['text'] = text
    id = xmlroot.get('id')
    if id != None:
        tree['id'] = id
    name = xmlroot.get('name')
    if name != None:
        tree['name'] = name
    value = xmlroot.get('value')
    if value != None:
        tree['value'] = value
    documentation = xmlroot.find('bpmn:documentation')
    if documentation != None:
        tree['documentation'] = documentation.text
    return tree

def paint_coords(image, tree, scaleperc):
    '''paint the href-tags as shapes to the image'''
    if 'subelements' in tree:
        for se in tree['subelements']:
            paint_coords(image, se, scaleperc)
    if 'tag' in tree:
        for t in tagstopaint.keys():
            if t in tree['tag']:
                if 'bounds' in tree:
                    x = tree['bounds']['x']
                    y = tree['bounds']['y']
                    h = tree['bounds']['h']
                    w = tree['bounds']['w']
                    if tagstopaint[t] == 'circle':
                        cv2.circle(image, (int(x + (w / 2)), int(y + (h / 2))), int(h / 2), (0, 20, 200), 10)
                        tree['mapcoords'] = str(int((x+(w/2)) * (scaleperc / 100))) + "," + \
                                            str(int((y+(h/2)) * (scaleperc / 100))) + "," + \
                                            str(int((h/2) * (scaleperc / 100)))
                        tree['mapshape'] = 'circle'
                    elif tagstopaint[t] == 'rect':
                        cv2.rectangle(image, (int(x), int(y)), (int(x+w), int(y+h)), (0, 20, 200), 10)
                        tree['mapcoords'] = str(int(x * (scaleperc / 100))) + "," + \
                                            str(int(y * (scaleperc / 100))) + "," + \
                                            str(int((x+w) * (scaleperc / 100))) + "," + \
                                            str(int((y+h) * (scaleperc / 100)))
                        tree['mapshape'] = 'rect'
                    elif tagstopaint[t] == 'poly':
                        rombus = np.array([(int(x + w / 2), int(y)),
                                           (int(x + w), int(y + h / 2)),
                                           (int(x + w / 2), int(y + h)),
                                           (int(x), int(y + h / 2))])
                        cv2.drawContours(image, [rombus], -1, (0, 20, 200), 10)
                        tree['mapcoords'] = str(int((x+(w/2)) * (scaleperc / 100))) + "," + \
                                            str(int(y * (scaleperc / 100))) + "," + \
                                            str(int((x+w) * (scaleperc / 100))) + "," + \
                                            str(int((y+(h/2)) * (scaleperc / 100))) + "," + \
                                            str(int((x+(w/2)) * (scaleperc / 100))) + "," + \
                                            str(int((y+h) * (scaleperc / 100))) + "," + \
                                            str(int(x * (scaleperc / 100)))+ "," + \
                                            str(int((y+(h/2)) * (scaleperc / 100)))
                        tree['mapshape'] = tagstopaint[t]


def gen_table_of_docks(tree):
    '''generate the dokumentation table for the html'''
    retstring = ''
    if 'subelements' in tree:
        for se in tree['subelements']:
            retstring += gen_table_of_docks(se)
    for i in tagstopaint.keys():
        if i in tree['tag']:
            if 'mapcoords' in tree:
                retstring += '      <tr>\n'
                retstring += '        <td><a name="{}">'.format(tree['id'])
                if 'name' in tree:
                    retstring += enc('{}'.format(tree['name']))
                else:
                    retstring += enc('"{}" has no name'.format(enc(tree['id'])))
                retstring += '</a></td>\n'
                if 'documentation' in tree:
                    retstring += '        <td>{}</td>\n'.format(enc(tree['documentation']))
                else:
                    retstring += '        <td></td>\n'
                if 'link' in tree:
                    retstring += '        <td><a href="{}">{}</a></td>\n'.format(tree['link'], tree['link'])
                else:
                    retstring += '        <td></td>\n'
                retstring += '      </tr>\n'
    return retstring


def get_bounds(xmlroot, id, namespace, xoffs, yoffs):
    '''Get bounds information from xmlelement'''
    test = xmlroot.find(".//bpmndi:BPMNShape[@bpmnElement='" + id + "']", namespace)
    if test is None:  # processes do not deliver coordinates.
        return None
    test = test.findall("./dc:Bounds", namespace)
    test = test[0]
    x = float(test.get("x")) * mult + xoffs
    y = float(test.get("y")) * mult + yoffs
    w = float(test.get("width")) * mult  # +xoffs
    h = float(test.get("height")) * mult
    return {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}

def read_bounds(tree, xmlroot, namespace, xoffs, yoffs):
    '''search bound information and insert it in to the tree element'''
    if 'subelements' in tree:
        for se in tree['subelements']:
            read_bounds(se, xmlroot, namespace, xoffs, yoffs)
    if 'id' in tree:
        bounds = get_bounds(xmlroot, tree['id'], namespace, xoffs, yoffs)
        if bounds != None:
            tree['bounds'] = get_bounds(xmlroot, tree['id'], namespace, xoffs, yoffs)

def get_diagrammmap(tree):
    '''return map elements extracted from the tree'''
    retstring = ''
    if 'subelements' in tree:
        for sub in tree['subelements']:
            retstring = retstring + get_diagrammmap(sub)
    if 'name' in tree:
        name = tree['name']
    else:
        name = ''
    if 'documentation' in tree:
        doc = tree['documentation']
    else:
        doc = ''
    for i in tagstopaint:
        if i in tree['tag']:
            if 'mapcoords' in tree:
                return '      <area shape="' + tree['mapshape'] + \
                       '" coords="' + tree['mapcoords'] + '" href="#' + \
                       tree['id'] + '" title="' + enc(name)+enc(doc) + \
                       '">\n' + retstring
    return retstring


def parse_TasksAndData(xmlroot, image, scaleperc, namespace, xoffs, yoffs):
    '''build the elemental tree and draw the shapes on the image'''
    global eltree
    eltree = build_tree(xmlroot)
   #For Debug you can write the tree to a file
    read_bounds(eltree, xmlroot, namespace, xoffs, yoffs)
    f = open('file.json', 'w')
    f.write(json.dumps(eltree, indent=4, sort_keys=True))
    f.close()
    paint_coords(image, eltree, scaleperc)


def processFile(filexml):
    '''read the given xml file and associated image and generate the html version'''
    xmlnamespace = {
    'xsi' : "http://www.w3.org/2001/XMLSchema-instance",
    'bpmn' : "http://www.omg.org/spec/BPMN/20100524/MODEL",
    'bpmndi' : "http://www.omg.org/spec/BPMN/20100524/DI",
    'dc' : "http://www.omg.org/spec/DD/20100524/DC",
    'di' : "http://www.omg.org/spec/DD/20100524/DI",
    'camunda' : "http://camunda.org/schema/1.0/bpmn"}

    print("processing file", filexml)

    filebase, _ = os.path.splitext(filexml)

    # read master image
    image_master = cv2.imread(filebase + ".png")
    if image_master is None:  # no image for this bpmn
        print("no image supplied for", filexml)
        return
    imageheight, imagewidth, _ = image_master.shape

    resizedimagewidth = 1850

    scale_percent = 100*(resizedimagewidth / float(image_master.shape[1])) # percent of original size for resizedimagewidth width

    tree = ElementTree.parse(filebase+".bpmn")
    root = tree.getroot()
    xmlwidth, xmlheight, xmin, ymin = parse_bpmn_bounds(root, xmlnamespace)

    xoffs = int(-xmin + (imagewidth - xmlwidth) / 2)
    yoffs = int(-ymin + (imageheight - xmlheight) / 2)

    parse_TasksAndData(root, image_master, scale_percent, xmlnamespace, xoffs, yoffs)

    width = int(image_master.shape[1] * scale_percent / 100)
    height = int(image_master.shape[0] * scale_percent / 100)
    dim = (width, height)
    otherimg = cv2.resize(image_master, dim, cv2.INTER_AREA)
    cv2.imwrite(filebase+"_k.png", otherimg)

    f = open(filebase+".html", "w")
    f.write('''
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>'''+filexml+'''</title>
    <meta name="viewport" content="width=device-width">
  </head>
  <style>
    body { 
      font-family: Helvetica, Arial, Geneva, sans-serif;
      }
    table, th, td {
      border: 1px solid black;
      border-collapse: collapse;
      }
    th, td {
      padding: 15px;
      }
  </style>      
  <body>
    <!-- page content -->    
    <h1> '''+filexml+'</h1>'+ datetime.now().strftime("%Y-%m-%d %H:%M:%S") +'''
    <p>
      <img src="'''+filebase+"_k.png"+'''" alt="The Process" usemap="#diagrammap" border="0" >
    </p>
    <map name="diagrammap">
''')
    f.write(get_diagrammmap(eltree))
    f.write('''    </map>
    <table style="width:'''+str(resizedimagewidth)+'''px">
      <tr>
        <th style="width:200px">name</th>
        <th>documentation</th> 
        <th style="width:200px">link</th>
      </tr>
''')

    f.write(gen_table_of_docks(eltree))
    f.write('''    </table>
  </body>
</html>
''')

    f.close()


for file in os.listdir("."):
    if file.endswith(".bpmn"):
        processFile(file)

