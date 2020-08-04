from xml.etree import ElementTree
import cv2 # pip install openCV-python
import os
from datetime import datetime

mult = 3  # fixed value to multiply xml values to get the image values


def paint_coordinates():
    global i, rx, ry, rw, rh
    # paint the result
    for i in bounds:
        rx = int(i.get('x')) * mult
        ry = int(i.get('y')) * mult
        rw = int(i.get('width')) * mult
        rh = int(i.get('height')) * mult

        cv2.circle(image_master, (rx + xoffs, ry + yoffs), 10, (200, 0, 0), 5)
        cv2.circle(image_master, ((rx + rw) + xoffs, ry + yoffs), 10, (200, 0, 0), 5)
        cv2.circle(image_master, (rx + xoffs, (ry + rh) + yoffs), 10, (200, 0, 0), 5)
        cv2.circle(image_master, ((rx + rw) + xoffs, (ry + rh) + yoffs), 10, (200, 0, 0), 5)
    cv2.rectangle(image_master, (xmin + xoffs, ymin + yoffs), (xmax + xoffs, ymax + yoffs), (0, 200, 0), 5)


def check_links(element, namespace):
    if element is None:
        print("checked empty element")
        return "","","",""
    theID = element.get('id')
    theName = element.get('name')
    if theName is None:
        theName = ""
    maybedoc = element.find("./bpmn:documentation", namespace)
    theDoc = ""
    if maybedoc is not None:
        theDoc = maybedoc.text
    cands = list(element.findall('./bpmn:extensionElements/camunda:properties/camunda:property', namespace))
    # cands = list(element.findall('.//*/camunda:property', namespace))
    theLink = ""
    for j in cands:
        if j.get('name') == 'link':
            theLink = j.get('value')
            #if theLink != "":
                # print(theID, "->", theLink)
    return theID, theLink, theName, theDoc


def find_coords(root, idx, xoffs, yoffs, scaleperc, namespace, image):
    global image_master
    global mult
    test = root.find(".//bpmndi:BPMNShape[@bpmnElement='" + idx + "']", namespace)
    if test is None:  # processes do not deliver coordinates.
        return ""
    test = test.findall("./dc:Bounds", namespace)
    test = test[0]
    x1 = float(test.get("x")) * mult +xoffs
    y1 = float(test.get("y")) * mult +yoffs
    w = float(test.get("width")) * mult # +xoffs
    h = float(test.get("height")) * mult
    x2 = x1 + w
    y2 = y1 + h
    theCoords = str(int(x1*(scaleperc/100))) + "," + str(int(y1*(scaleperc/100))) + "," + str(int(x2*(scaleperc/100))) + "," + str(int(y2*(scaleperc/100))) # on windows
    # theCoords = str(int(x1)) + "," + str(int(y1)) + "," + str(int(x2)) + "," + str(int(y2))

    cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 20, 200), 20)

    return theCoords


def enc(st):
    st = st.replace("\"", '&quot;')
    encod = st.encode(encoding="ascii", errors="xmlcharrefreplace")
    decod = encod.decode("utf-8")
    return decod


# read xml for max size
def parse_bpmn_bounds(xmlroot, namespace):  # -> (x,y)
    bounds = xmlroot.findall("bpmndi:BPMNDiagram/bpmndi:BPMNPlane/bpmndi:BPMNShape/dc:Bounds", namespace)
    bounds = bounds + xmlroot.findall("bpmndi:BPMNDiagram/bpmndi:BPMNPlane/bpmndi:BPMNShape/bpmndi:BPMNLabel/dc:Bounds", namespace)

    # find the outer bounds
    xmin = 20000
    xmax = -20000
    ymin = 20000
    ymax = -20000
    for i in bounds:
        rx = int(i.get('x')) * mult
        ry = int(i.get('y')) * mult
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


def parse_TasksAndData(xmlroot, namespace, xoffs, yoffs, scale_percent, image, items):
    itemkeys = ["id","name","doc","link","coords","size"]
    # find all task activities. This is the point, where we start from.
    tasks = xmlroot.findall("./bpmn:process", namespace)
    tasks = tasks + xmlroot.findall("./bpmn:collaboration", namespace)
    tasks = tasks + xmlroot.findall("*/bpmn:startEvent", namespace)
    tasks = tasks + xmlroot.findall("*/bpmn:task", namespace)
    tasks = tasks + xmlroot.findall("*/bpmn:userTask", namespace)
    tasks = tasks + xmlroot.findall("*/bpmn:serviceTask", namespace)
    tasks = tasks + xmlroot.findall("*/bpmn:endEvent", namespace)
    sp = xmlroot.findall("*/bpmn:subProcess", namespace)
    if len(sp) != 0:
        print('Subprocess "' + sp[0].attrib['name'] + '" is not fully supported.')  # fixme support it, when needed.
        sp[0].attrib['name'] = '[UNSUPPORTED]'+sp[0].attrib['name']
        tasks = tasks + sp

    for ac in tasks:
        idx, lnk, nme, doc = check_links(ac, namespace)
        # print("actID:", idx)
        # have an entry for every task
        if idx is not None:
            # print(idx, "->", lnk)
            tc = find_coords(xmlroot, idx, xoffs, yoffs, scale_percent, namespace, image)
            # print("tst", tc)  # html: x1,y1,x2,y2
            items.append(dict(zip(itemkeys, [idx, nme, doc, lnk, tc, 2])))

        # find all arrows pointing away from this task with the targeted elements
        dors = ac.findall(".//bpmn:targetRef", namespace)
        dors = dors + ac.findall(".//bpmn:sourceRef", namespace)

        for d2 in dors:
            idx2 = d2.text
            # print("tref:", idx2)

            # find target elements of the arrows, can only be one direction!
            j = xmlroot.find(".//bpmn:dataStoreReference[@id='" + idx2 + "']", namespace)
            k = xmlroot.find(".//bpmn:dataObjectReference[@id='" + idx2 + "']", namespace)
            if j is not None:
                idx, lnk, nme, doc = check_links(j, namespace)
            else:
                idx, lnk, nme, doc = check_links(k, namespace)
            # print(idx, "->", lnk, nme)
            if idx != "":
                # print(idx, "->", lnk)
                tc = find_coords(xmlroot, idx, xoffs, yoffs, scale_percent, namespace, image)
                # print("tst", tc)  # html: x1,y1,x2,y2
                items.append(dict(zip(itemkeys, [idx, nme, doc, lnk, tc, 4])))


def processFile(filexml):
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

    resizedimagewidth = 1200

    scale_percent = 100*(resizedimagewidth / float(image_master.shape[1])) # percent of original size for resizedimagewidth width

    tree = ElementTree.parse(filebase+".bpmn")
    root = tree.getroot()
    xmlwidth, xmlheight, xmin, ymin = parse_bpmn_bounds(root, xmlnamespace)

    xoffs = int(-xmin + (imagewidth - xmlwidth) / 2)
    yoffs = int(-ymin + (imageheight - xmlheight) / 2)
    # print("image size:",imagewidth,imageheight)
    # print("xml size:",xmlwidth,xmlheight)

    # paint_coordinates() # fixme is defective !!

    items = []

    parse_TasksAndData(root, xmlnamespace, xoffs, yoffs, scale_percent, image_master, items)

    # not necessary: cv2.imwrite(filebase+"2.png", image_master)


    width = int(image_master.shape[1] * scale_percent / 100)
    height = int(image_master.shape[0] * scale_percent / 100)
    dim = (width, height)
    otherimg = cv2.resize(image_master, dim, cv2.INTER_AREA)
    cv2.imwrite(filebase+"_k.png", otherimg)

    # cv2.imshow('Window', otherimg)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()


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
    <img src="'''+filebase+".png"+'''" alt="The Process" border="0" width="100%">
    <img src="'''+filebase+"_k.png"+'''" alt="The Process" usemap="#diagrammap" border="0" >
    </p>
    <map name="diagrammap">
      ''')
    # <area shape="rect" coords="835,85,885,135" href="http://DataStoreReference_1qi69ag" alt="DataStoreReference_1qi69ag" title="rechtsoben">
    for i in items:
        f.write(' <area shape="rect" coords="'+i['coords']+'" href="#'+i['id']+'" title="'+enc(i['name'])+'\n'+enc(i['doc'])+'">\n')

    f.write('''
    </map>
    <table style="width:'''+str(resizedimagewidth)+'''px">
      <tr>
        <th style="width:200px">name</th>
        <th>documentation</th> 
        <th style="width:200px">link</th>
      </tr>
    ''')

    for i in items:
        n = i['name']
        d = i['doc']
        l = i['link']
        s = str(i['size'])
        f.write('\n<tr>')
        f.write('<td>')
        f.write('<a name="' + i['id'] + '">')
        if n == "":
            f.write( i['id'] + ' has no name\n')
        else:  # elif d != "" or l != "":
            if s == '4':
                f.write( enc(n) +'\n')
            else:
                f.write('<h'+s+'>'+enc(n)+'</h'+s+'>\n')
        f.write('</a>\n')
        f.write('</td><td>')
        f.write(enc(d.replace('\n', '<br>\n'))+'\n')
        f.write('</td><td>')
        f.write('<a href="'+l+'">'+l+'</a>\n')
        f.write('</td>')
        # else: # has only name and nothing more.
        #     f.write('<td>')
        #     f.write('<a name="' + i['id'] + '">')
        #     f.write(enc(n) + '\n')
        #     f.write('</a>\n')
        #     f.write('</td><td></td><td></td>')  # empty
        f.write('</tr>')


    # resizeable map code
    # <script src="http://ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
    # <script type="text/javascript" src="./imageMapResizer.min.js"></script>
    #     <script type="text/javascript">
    #         $('map').imageMapResize();
    # </script>

    f.write('''
    
    
        </body>
    </html>
    ''')

    f.close()


# processFile("einer.bpmn")

for file in os.listdir("."):
    if file.endswith(".bpmn"):
        processFile(file)

