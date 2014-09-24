# coding=utf-8
__author__ = "Chris Dieringer <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import copy

# Recursively merges two dictionaries.  On collisions where both values are
# also dictionaries, those dictionaries are also merged
# partial credit: xormedia.com/recursively-merge-dictionaries-in-python/
def dict_merge(a, b):
	if (not isinstance(a, dict) or not isinstance(b, dict)):
		raise Exception("invalid dictionary passed")
	return _dict_merge(a, b)

def _dict_merge(a, b):
	if not isinstance(b, dict):
		return b
	result = copy.deepcopy(a)
	for k, v in b.items():
		if k in result:
			if isinstance(result[k], dict):
				result[k] = dict_merge(result[k], v)
			else:
				raise Exception("merge collision on key: " + k)
		else:
			result[k] = copy.deepcopy(v)
	return result


# Iterates through each node of an Dictionary, recursively
# on property values of type Dictionary.
# @param  {*} node initially fed the root Dictionary to recurse through
# @param  {Dictionary} config {
#     on: function(...) // executes at each node
#     mode: "array"|null // what is returned by the root call
#     _init: toggled true during the first node's execution
#     _path: ["prop", "subprop_of_prop", ...etc]. path array of current node
# }
# @return {Array}
def eachDeep(node, config):
	if "_init" not in config.keys():
		config["_init"] = True
		config["_path"] = []
		if "mode" not in config.keys():
			config["mode"] = None
	if node is None or not isinstance(node, dict):
		# return config["on"](node, config)
		return config["on"](node, config)
	nodeResults = []
	for k, v in node.items():
		config["_path"].append(k)
		subResults = eachDeep(v, config)
		if config["mode"] == "array":
			nodeResults.extend(subResults)
		if config["_path"]:
			config["_path"].pop()
	return nodeResults
