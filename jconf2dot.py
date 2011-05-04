#!/usr/bin/env python
# jconf2dot.py - parse a VR Juggler jconf file and output graphviz "dot"-format files
# Author: Ryan Pavlik

# https://github.com/rpavlik/jconf-grapher

#          Copyright Iowa State University 2011.
# Distributed under the Boost Software License, Version 1.0.
#    (See accompanying file LICENSE_1_0.txt or copy at
#          http://www.boost.org/LICENSE_1_0.txt)

import xml.etree.cElementTree as et
import sys

links = []
definedNodes = []
usedNodes = []
filequeue = []

ns = "{http://www.vrjuggler.org/jccl/xsd/3.0/configuration}"

ignoredElements = ["input_manager",
	"display_system",
	"corba_remote_reconfig",
	"display_window", # for now, until we recurse into it to find the kb/mouse device, the user for surface projections, and proxies for simulator
	"cluster_node", #ditto
	"cluster_manager",
	"start_barrier_plugin",
	"application_data"
	]

def sanitize(name):
	"""Turn an arbitrary string into something we can use as an ID in a dot file"""
	return name.replace(" ", "_").replace(".jconf", "").replace("/", "_").replace("\\", "_").replace(".", "_").replace("-", "_")

def outputNode(name, eltType = "", style = ""):
	"""Print dot code to display a node as requested"""
	if "proxy" in eltType:
		pass
	elif "alias" in eltType:
		style = style + "style=filled,color=lightgray,"
	elif "user" in eltType:
		style = style + "shape=egg,"
	else:
		style = style + "shape=box3d,"
	if eltType == "":
		label = name
	else:
		label = "%s\\n[%s]" % (name, eltType)
	print('%s [%slabel = "%s"];' % (sanitize(name), style, label))

def addNode(elt, style = ""):
	"""Given an element, output the appropriate dot code for the node and mark it as 'recognized'"""
	eltName = elt.get("name")
	eltType = elt.tag.replace(ns, "")
	definedNodes.append(sanitize(eltName))


	#print('%s [%slabel = <%s<br/><i>%s</i> >];' % (sanitize(eltName), style, eltName, eltType))
	outputNode(eltName, eltType, style)

def addLink(src, dest, label = None):
	"""Add a link between src and dest, with an optional label"""
	usedNodes.extend([sanitize(src), sanitize(dest)])
	if label is None:
		links.append("%s -> %s;" % (sanitize(src), sanitize(dest)))
	else:
		links.append('%s -> %s [label = "%s"];' % (sanitize(src), sanitize(dest), label))

def handleAlias(elt):
	"""Add the link implied by an alias element."""
	addLink(elt.get("name"), elt.findtext(ns + "proxy"))

def handleProxy(elt, proxyType = None):
	"""Add the link implied by a proxy element."""
	if proxyType is not None:
		label = proxyType
		unit = elt.findtext(ns + "unit")
		if unit is not None:
			label = "%s Unit %s" % (proxyType, unit)
		addLink(elt.get("name"), elt.findtext(ns + "device"), label)
	else:
		addLink(elt.get("name"), elt.findtext(ns + "device"))

def handleUser(elt):
	"""Add the head position link implied by a user element."""
	addLink(elt.get("name"), elt.findtext(ns + "head_position"), "Head Position")

def handleSimulated(elt):
	"""Add the kb/mouse proxy link implied by a simulated device element."""
	addLink(elt.get("name"), elt.findtext(ns + "keyboard_mouse_proxy"), "uses")

def processFile(filename):
	"""Print a cluster of nodes based on a jconf file, and process any links"""
	print("subgraph cluster_%s {" % sanitize(filename))

	print('label = "%s";' % filename)
	print('style = "dotted";')

	tree = et.parse(filename)
	root = tree.getroot()
	included = []

	for firstLevel in list(root):
		if firstLevel.tag == ns + "include":
			# recurse into included file
			processFile(firstLevel.text)

		elif firstLevel.tag == ns + "elements":

			for elt in list(firstLevel):
				# Some tags we ignore.
				if elt.tag in [ns + x for x in ignoredElements]:
					continue

				# Add nodes for the rest of the elements
				addNode(elt)

				# Some nodes contain information on relationships
				# that we want to depict in the graph.
				if elt.tag == ns + "alias":
					handleAlias(elt)

				elif elt.tag == ns + "position_proxy":
					handleProxy(elt, "Position")

				elif elt.tag == ns + "analog_proxy":
					handleProxy(elt, "Analog")

				elif elt.tag == ns + "digital_proxy":
					handleProxy(elt, "Digital")

				elif elt.tag == ns + "keyboard_mouse_proxy":
					handleProxy(elt)

				elif elt.tag == ns + "user":
					handleUser(elt)

				elif ns + "simulated" in elt.tag:
					handleSimulated(elt)

		else:
			continue



	print("}")
	return included

def addUndefinedNodes():
	"""Output all nodes referenced but not defined, with special formatting"""

	undefined = [ x for x in usedNodes if x not in definedNodes ]
	if len(undefined) > 0:
		print("subgraph cluster_undefined {")
		print('label = "Not defined in these files";')
		print('style = "dotted";')
		for node in undefined:
			outputNode(node, style = "style=dashed,")
		print("}")

def processFiles(files):
	"""Process all jconf files passed, printing the complete dot output."""

	print("digraph {")
	print('size="8.5,11"')
	print('ratio="compress"')
	for file in files:
		processFile(file)
	addUndefinedNodes()
	print( "\n".join(links))
	print("}")

if __name__ == "__main__":
	processFiles(sys.argv[1:])
