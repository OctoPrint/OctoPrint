# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import os
import mock

from ddt import ddt, unpack, data

import octoprint.filemanager.storage


class FileWrapper(object):
	def __init__(self, filename):
		self.path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "_files", filename)

		import hashlib
		blocksize = 65536
		hash = hashlib.sha1()
		with open(self.path, "rb") as f:
			buffer = f.read(blocksize)
			while len(buffer) > 0:
				hash.update(buffer)
				buffer = f.read(blocksize)
		self.hash = hash.hexdigest()

	def save(self, destination):
		import shutil
		shutil.copy(self.path, destination)

FILE_BP_CASE_STL = FileWrapper("bp_case.stl")
FILE_BP_CASE_GCODE = FileWrapper("bp_case.gcode")
FILE_CRAZYRADIO_STL = FileWrapper("crazyradio.stl")

@ddt
class LocalStorageTest(unittest.TestCase):

	def setUp(self):
		import tempfile
		self.basefolder = tempfile.mkdtemp()
		self.storage = octoprint.filemanager.storage.LocalFileStorage(self.basefolder)

		# mock file manager module
		self.filemanager_patcher = mock.patch("octoprint.filemanager")
		self.filemanager = self.filemanager_patcher.start()

		self.filemanager.valid_file_type.return_value = True

		def get_file_type(name):
			if name.lower().endswith(".stl"):
				return ["model", "stl"]
			elif name.lower().endswith(".gco") or name.lower().endswith(".gcode") or name.lower.endswith(".g"):
				return ["machinecode", "gcode"]
			else:
				return None
		self.filemanager.get_file_type.side_effect = get_file_type

	def tearDown(self):
		import shutil
		shutil.rmtree(self.basefolder)

		self.filemanager_patcher.stop()

	def test_add_file(self):
		self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)

	def test_add_file_overwrite(self):
		self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)

		try:
			self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL, overwrite=False)
		except:
			pass

		self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL, overwrite=True)

	def test_add_file_with_web(self):
		import time
		href = "http://www.example.com"
		retrieved = time.time()

		stl_name = self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL, links=[("web", dict(href=href, retrieved=retrieved))])
		stl_metadata = self.storage.get_metadata(stl_name)

		self.assertIsNotNone(stl_metadata)
		self.assertEquals(1, len(stl_metadata["links"]))
		link = stl_metadata["links"][0]
		self.assertTrue("web", link["rel"])
		self.assertTrue("href" in link)
		self.assertEquals(href, link["href"])
		self.assertTrue("retrieved" in link)
		self.assertEquals(retrieved, link["retrieved"])

	def test_add_file_with_association(self):
		stl_name = self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)
		gcode_name = self._add_file("bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE, links=[("model", dict(name=stl_name))])

		stl_metadata = self.storage.get_metadata(stl_name)
		gcode_metadata = self.storage.get_metadata(gcode_name)

		# forward link
		self.assertEquals(1, len(gcode_metadata["links"]))
		link = gcode_metadata["links"][0]
		self.assertEquals("model", link["rel"])
		self.assertTrue("name" in link)
		self.assertEquals(stl_name, link["name"])
		self.assertTrue("hash" in link)
		self.assertEquals(FILE_BP_CASE_STL.hash, link["hash"])

		# reverse link
		self.assertEquals(1, len(stl_metadata["links"]))
		link = stl_metadata["links"][0]
		self.assertEquals("machinecode", link["rel"])
		self.assertTrue("name" in link)
		self.assertEquals(gcode_name, link["name"])
		self.assertTrue("hash" in link)
		self.assertEquals(FILE_BP_CASE_GCODE.hash, link["hash"])

	def test_remove_file(self):
		stl_name = self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)
		gcode_name = self._add_file("bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE, links=[("model", dict(name=stl_name))])

		stl_metadata = self.storage.get_metadata(stl_name)
		gcode_metadata = self.storage.get_metadata(gcode_name)

		self.assertIsNotNone(stl_metadata)
		self.assertIsNotNone(gcode_metadata)

		self.storage.remove_file(stl_name)
		self.assertFalse(os.path.exists(os.path.join(self.basefolder, stl_name)))

		stl_metadata = self.storage.get_metadata(stl_name)
		gcode_metadata = self.storage.get_metadata(gcode_name)

		self.assertIsNone(stl_metadata)
		self.assertIsNotNone(gcode_metadata)

		self.assertEquals(0, len(gcode_metadata["links"]))

	def test_add_folder(self):
		self._add_folder("test", "test")

	def test_add_subfolder(self):
		folder_name = self._add_folder("folder with some spaces", "folder_with_some_spaces")
		subfolder_name = self._add_folder((folder_name, "subfolder"), folder_name + "/subfolder")
		stl_name = self._add_file((subfolder_name, "bp_case.stl"), subfolder_name + "/bp_case.stl", FILE_BP_CASE_STL)

		self.assertTrue(os.path.exists(os.path.join(self.basefolder, folder_name)))
		self.assertTrue(os.path.exists(os.path.join(self.basefolder, subfolder_name)))
		self.assertTrue(os.path.exists(os.path.join(self.basefolder, stl_name)))

	def test_remove_folder(self):
		content_folder = self._add_folder("content", "content")
		other_stl_name = self._add_file((content_folder, "crazyradio.stl"), content_folder + "/crazyradio.stl", FILE_CRAZYRADIO_STL)

		empty_folder = self._add_folder("empty", "empty")

		try:
			self.storage.remove_folder(content_folder, recursive=False)
		except:
			self.assertTrue(os.path.exists(os.path.join(self.basefolder, content_folder)))
			self.assertTrue(os.path.isdir(os.path.join(self.basefolder, content_folder)))
			self.assertTrue(os.path.exists(os.path.join(self.basefolder, other_stl_name)))
			self.assertIsNotNone(self.storage.get_metadata(other_stl_name))

		self.storage.remove_folder(content_folder, recursive=True)
		self.assertFalse(os.path.exists(os.path.join(self.basefolder, content_folder)))
		self.assertFalse(os.path.isdir(os.path.join(self.basefolder, content_folder)))

		self.storage.remove_folder(empty_folder, recursive=False)
		self.assertFalse(os.path.exists(os.path.join(self.basefolder, empty_folder)))
		self.assertFalse(os.path.isdir(os.path.join(self.basefolder, empty_folder)))

	def test_remove_folder_with_metadata(self):
		content_folder = self._add_folder("content", "content")
		other_stl_name = self._add_file((content_folder, "crazyradio.stl"), content_folder + "/crazyradio.stl", FILE_CRAZYRADIO_STL)
		self.storage.remove_file(other_stl_name)

		self.storage.remove_folder(content_folder, recursive=False)

	def test_list(self):
		bp_case_stl = self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)
		self._add_file("bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE, links=[("model", dict(name=bp_case_stl))])

		content_folder = self._add_folder("content", "content")
		self._add_file((content_folder, "crazyradio.stl"), content_folder + "/crazyradio.stl", FILE_CRAZYRADIO_STL)

		self._add_folder("empty", "empty")

		file_list = self.storage.list_files()
		self.assertEquals(4, len(file_list))
		self.assertTrue("bp_case.stl" in file_list)
		self.assertTrue("bp_case.gcode" in file_list)
		self.assertTrue("content" in file_list)
		self.assertTrue("empty" in file_list)

		self.assertEquals("model", file_list["bp_case.stl"]["type"])
		self.assertEquals(FILE_BP_CASE_STL.hash, file_list["bp_case.stl"]["hash"])

		self.assertEquals("machinecode", file_list["bp_case.gcode"]["type"])
		self.assertEquals(FILE_BP_CASE_GCODE.hash, file_list["bp_case.gcode"]["hash"])

		self.assertEquals("folder", file_list[content_folder]["type"])
		self.assertEquals(1, len(file_list[content_folder]["children"]))
		self.assertTrue("crazyradio.stl" in file_list["content"]["children"])
		self.assertEquals("model", file_list["content"]["children"]["crazyradio.stl"]["type"])
		self.assertEquals(FILE_CRAZYRADIO_STL.hash, file_list["content"]["children"]["crazyradio.stl"]["hash"])

		self.assertEquals("folder", file_list["empty"]["type"])
		self.assertEquals(0, len(file_list["empty"]["children"]))

	def test_add_link_model(self):
		stl_name = self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)
		gcode_name = self._add_file("bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE)

		self.storage.add_link(gcode_name, "model", dict(name=stl_name))

		stl_metadata = self.storage.get_metadata(stl_name)
		gcode_metadata = self.storage.get_metadata(gcode_name)

		# forward link
		self.assertEquals(1, len(gcode_metadata["links"]))
		link = gcode_metadata["links"][0]
		self.assertEquals("model", link["rel"])
		self.assertTrue("name" in link)
		self.assertEquals(stl_name, link["name"])
		self.assertTrue("hash" in link)
		self.assertEquals(FILE_BP_CASE_STL.hash, link["hash"])

		# reverse link
		self.assertEquals(1, len(stl_metadata["links"]))
		link = stl_metadata["links"][0]
		self.assertEquals("machinecode", link["rel"])
		self.assertTrue("name" in link)
		self.assertEquals(gcode_name, link["name"])
		self.assertTrue("hash" in link)
		self.assertEquals(FILE_BP_CASE_GCODE.hash, link["hash"])

	def test_add_link_machinecode(self):
		stl_name = self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)
		gcode_name = self._add_file("bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE)

		self.storage.add_link(stl_name, "machinecode", dict(name=gcode_name))

		stl_metadata = self.storage.get_metadata(stl_name)
		gcode_metadata = self.storage.get_metadata(gcode_name)

		# forward link
		self.assertEquals(1, len(gcode_metadata["links"]))
		link = gcode_metadata["links"][0]
		self.assertEquals("model", link["rel"])
		self.assertTrue("name" in link)
		self.assertEquals(stl_name, link["name"])
		self.assertTrue("hash" in link)
		self.assertEquals(FILE_BP_CASE_STL.hash, link["hash"])

		# reverse link
		self.assertEquals(1, len(stl_metadata["links"]))
		link = stl_metadata["links"][0]
		self.assertEquals("machinecode", link["rel"])
		self.assertTrue("name" in link)
		self.assertEquals(gcode_name, link["name"])
		self.assertTrue("hash" in link)
		self.assertEquals(FILE_BP_CASE_GCODE.hash, link["hash"])

	def test_remove_link(self):
		stl_name = self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)

		self.storage.add_link(stl_name, "web", dict(href="http://www.example.com"))
		self.storage.add_link(stl_name, "web", dict(href="http://www.example2.com"))

		stl_metadata = self.storage.get_metadata(stl_name)
		self.assertEquals(2, len(stl_metadata["links"]))

		self.storage.remove_link(stl_name, "web", dict(href="http://www.example.com"))

		stl_metadata = self.storage.get_metadata(stl_name)
		self.assertEquals(1, len(stl_metadata["links"]))

		self.storage.remove_link(stl_name, "web", dict(href="wrong_href"))

		stl_metadata = self.storage.get_metadata(stl_name)
		self.assertEquals(1, len(stl_metadata["links"]))

	def test_remove_link_bidirectional(self):
		stl_name = self._add_file("bp_case.stl", "bp_case.stl", FILE_BP_CASE_STL)
		gcode_name = self._add_file("bp_case.gcode", "bp_case.gcode", FILE_BP_CASE_GCODE)

		self.storage.add_link(stl_name, "machinecode", dict(name=gcode_name))
		self.storage.add_link(stl_name, "web", dict(href="http://www.example.com"))

		stl_metadata = self.storage.get_metadata(stl_name)
		gcode_metadata = self.storage.get_metadata(gcode_name)

		self.assertEquals(1, len(gcode_metadata["links"]))
		self.assertEquals(2, len(stl_metadata["links"]))

		self.storage.remove_link(gcode_name, "model", dict(name=stl_name, hash=FILE_BP_CASE_STL.hash))

		stl_metadata = self.storage.get_metadata(stl_name)
		gcode_metadata = self.storage.get_metadata(gcode_name)

		self.assertEquals(0, len(gcode_metadata["links"]))
		self.assertEquals(1, len(stl_metadata["links"]))

	@data(
		("some_file.gco", "some_file.gco"),
		("some_file with (parentheses) and ümläuts and digits 123.gco", "some_file_with_(parentheses)_and_umlauts_and_digits_123.gco"),
		("pengüino pequeño.stl", "penguino_pequeno.stl")
	)
	@unpack
	def test_sanitize_name(self, input, expected):
		actual = self.storage.sanitize_name(input)
		self.assertEquals(expected, actual)

	@data(
		"some/folder/still/left.gco",
		"also\\no\\backslashes.gco"
	)
	def test_sanitize_name_invalid(self, input):
		try:
			self.storage.sanitize_name(input)
			self.fail("expected a ValueError")
		except ValueError as e:
			self.assertEquals("name must not contain / or \\", e.message)

	@data(
		("folder/with/subfolder", "/folder/with/subfolder"),
		("folder/with/subfolder/../other/folder", "/folder/with/other/folder"),
		("/folder/with/leading/slash", "/folder/with/leading/slash"),
		("folder/with/leading/dot", "/folder/with/leading/dot")
	)
	@unpack
	def test_sanitize_path(self, input, expected):
		actual = self.storage.sanitize_path(input)
		self.assertTrue(actual.startswith(self.basefolder))
		self.assertEquals(expected, actual[len(self.basefolder):].replace(os.path.sep, "/"))

	@data(
		"../../folder/out/of/the/basefolder",
		"some/folder/../../../and/then/back"
	)
	def test_sanitize_path_invalid(self, input):
		try:
			self.storage.sanitize_path(input)
			self.fail("expected a ValueError")
		except ValueError as e:
			self.assertTrue(e.message.startswith("path not contained in base folder: "))

	@data(
		("some/folder/and/some file.gco", "/some/folder/and", "some_file.gco"),
		(("some", "folder", "and", "some file.gco"), "/some/folder/and", "some_file.gco"),
		("some file.gco", "/", "some_file.gco"),
		(("some file.gco",), "/", "some_file.gco"),
		("", "/", ""),
		("some/folder/with/trailing/slash/", "/some/folder/with/trailing/slash", ""),
		(("some", "folder", ""), "/some/folder", "")
	)
	@unpack
	def test_sanitize(self, input, expected_path, expected_name):
		actual = self.storage.sanitize(input)
		self.assertTrue(isinstance(actual, tuple))
		self.assertEquals(2, len(actual))

		actual_path, actual_name = actual
		self.assertTrue(actual_path.startswith(self.basefolder))
		actual_path = actual_path[len(self.basefolder):].replace(os.path.sep, "/")
		if not actual_path.startswith("/"):
			# if the actual path originally was just the base folder, we just stripped
			# away everything, so let's add a / again so the behaviour matches the
			# other preprocessing of our test data here
			actual_path = "/" + actual_path

		self.assertEquals(expected_path, actual_path)
		self.assertEquals(expected_name, actual_name)

	def _add_file(self, path, expected_path, file_object, links=None, overwrite=False):
		sanitized_path = self.storage.add_file(path, file_object, links=links, allow_overwrite=overwrite)
		split_path = sanitized_path.split("/")
		if len(split_path) == 1:
			file_path = os.path.join(self.basefolder, split_path[0])
			folder_path = self.basefolder
		else:
			file_path = os.path.join(self.basefolder, os.path.join(*split_path))
			folder_path = os.path.join(self.basefolder, os.path.join(*split_path[:-1]))

		self.assertEquals(expected_path, sanitized_path)
		self.assertTrue(os.path.exists(file_path))
		self.assertTrue(os.path.exists(os.path.join(folder_path, ".metadata.yaml")))

		metadata = self.storage.get_metadata(sanitized_path)
		self.assertIsNotNone(metadata)

		# assert hash
		self.assertTrue("hash" in metadata)
		self.assertEquals(file_object.hash, metadata["hash"])

		# assert presence of links if supplied
		if links:
			self.assertTrue("links" in metadata)

		return sanitized_path

	def _add_folder(self, path, expected_path):
		sanitized_path = self.storage.add_folder(path)
		self.assertEquals(expected_path, sanitized_path)
		self.assertTrue(os.path.exists(os.path.join(self.basefolder, os.path.join(*sanitized_path.split("/")))))
		self.assertTrue(os.path.isdir(os.path.join(self.basefolder, os.path.join(*sanitized_path.split("/")))))

		return sanitized_path

