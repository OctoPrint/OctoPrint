function FilemanagerViewModel() {
	var self = this;

	self.directoryContextMenu = $("#dirContextMenu");
	self.fileContextMenu = $("#fileContextMenu");
	self.rowClicked;

	$("#directoryTab").on("contextmenu", null, function (e) {
		self.rowClicked = $(this);
		self.directoryContextMenu.css({ display: "block", left: e.pageX, top: e.pageY });
		return false;
	});
	$("#fileTab").on("contextmenu", null, function (e) {
		self.rowClicked = $(this);
		self.fileContextMenu.css({ display: "block", left: e.pageX, top: e.pageY });
		return false;
	});

	$(document).click(function () {
		self.directoryContextMenu.hide();
		self.fileContextMenu.hide();
	});

	self.activeFolders = ko.observableArray([]);
	self.cutFolders = ko.observableArray([]);

	self.activeFiles = ko.observableArray([]);
	self.cutFiles = ko.observableArray([]);

	self.directoryList = ko.observableArray([]);

	self.itemList = ko.dependentObservable(function () {
		if (self.activeFolders() == undefined) {
			return [];
		} else {
			var folders = self.activeFolders();
			if (folders.length != 1)
				return [];

			return folders[0].files;
		}
	});

	self.requestData = function (filenameToFocus, locationToFocus) {
		$.ajax({
			url: API_BASEURL + "files",
			method: "GET",
			dataType: "json",
			success: function (response) {
				self.fromResponse(response, filenameToFocus, locationToFocus);
			}
		});
	};
	self.fromResponse = function (response, filenameToFocus, locationToFocus) {
		var files = response.files;

		var dirs = {};
		var looseFiles = [];

		_.each(files, function (element, index, list) {
			element.type = "file";
			if (!element.hasOwnProperty("relativepath")) {
				element.relativepath = "";
				looseFiles.push(element);
			}
			else {
				var path = element.relativepath.substring(0, element.relativepath.lastIndexOf("/"));
				if (path == "")
					looseFiles.push(element);
				else {
					var fullpath = "";
					var dir = dirs;
					while (path.indexOf("/") != -1) {
						var name = path.substring(0, path.indexOf("/"));
						if (!dir.hasOwnProperty(name))
							dir[name] = { name: name, path: fullpath, dirs: [], files: [] };

						dir = dirs[name];
						fullpath = fullpath + "/" + name;
						path = path.substring(path.indexOf("/"));
					}

					if (!dir.hasOwnProperty(path))
						dir[path] = { name: path, path: fullpath, dirs: [], files: [] };

					dir[path].files.push(element);
				}
			}
			if (!element.hasOwnProperty("size")) element.size = undefined;
			if (!element.hasOwnProperty("date")) element.date = undefined;
		});

		var upload = [
			{
				name: "Uploads",
				dirs: [],
				files: looseFiles
			}
		];

		_.each(dirs, function (element, index, list) {
			upload[0].dirs.push(element);
		});

		self.directoryList(upload);
	};

	self.displayMode = function (data) {
		if (data.dirs === undefined)
			return "singleDir";

		return data.dirs.length > 0 ? "expandableDir" : "singleDir";
	};

	self.isFolderSelected = function (data) {
		if (data === undefined || self.activeFolders() === undefined)
			return false;

		var itemList = self.activeFolders();
		for (var i = 0; i < itemList.length; i++) {
			if (itemList[i] == data) {
				return true;
			}
		}
		return false;
	};
	self.isFolderCut = function (data) {
		if (data === undefined || self.cutFolders() === undefined)
			return false;

		var itemList = self.cutFolders();
		for (var i = 0; i < itemList.length; i++) {
			if (itemList[i] == data) {
				return true;
			}
		}
		return false;
	};

	self.isFileSelected = function (data) {
		if (data === undefined || self.activeFiles() === undefined)
			return false;

		var itemList = self.activeFiles();
		for (var i = 0; i < itemList.length; i++) {
			if (itemList[i] == data) {
				return true;
			}
		}
		return false;
	};
	self.isFileCut = function (data) {
		if (data === undefined || self.cutFiles() === undefined)
			return false;

		var itemList = self.cutFiles();
		for (var i = 0; i < itemList.length; i++) {
			if (itemList[i] == data) {
				return true;
			}
		}
		return false;
	};

	self.selectFolder = function (data, e) {
		if (self.directoryContextMenu.css("display") == "block")
			return;

		var itemList = self.activeFolders();
		var index = itemList.indexOf(data);
		if (index == -1)
			if (e.ctrlKey)
				itemList.push(data);
			else
				itemList = [data];
		else
			if (e.ctrlKey)
				itemList.splice(index, 1);
			else if (itemList.length > 1)
				itemList = [data];
			else
				itemList = [];

		self.activeFolders(itemList);
		e.stopPropagation();
	}
	self.selectFile = function (data, e) {
		if (self.fileContextMenu.css("display") == "block")
			return;

		if (data == self)
		{
			self.activeFiles([]);
			e.stopPropagation();
			return;
		}

		var itemList = self.activeFiles();
		var index = itemList.indexOf(data);
		if (index == -1)
			if (e.ctrlKey)
				itemList.push(data);
			else
				itemList = [data];
		else
			if (e.ctrlKey)
				itemList.splice(index, 1);
			else if (itemList.length > 1)
				itemList = [data];
			else
				itemList = [];

		self.activeFiles(itemList);
		e.stopPropagation();
	}

	self.createFolder = function () {
		$("#renameName").val("");
		$("#renameName").keydown(function (e) {
			if (e.keyCode == 13)
			{
				e.preventDefault();
				$("#name_overlay").modal("hide");

				var value = $("#renameName").val();

				// AJAX Request

			}
		});
		$("#name_overlay").modal("show");
	};
	self.removeFolder = function () {
		var folders = self.activeFolders();

		// AJAX Request

		self.activeFolders([]);
	};
	self.cutFolder = function () {
		self.cutFolders(self.activeFolders());
		self.activeFolders([]);
	};
	self.pasteFolder = function () {
		var folder = self.activeFolders();
		var cutFolders = self.cutFolders();

		// AJAX Request

		self.activeFolders([]);
	};

	self.selectAll = function () {
		self.activeFiles(self.itemList());
	};
	self.deselectAll = function () {
		self.activeFiles([]);
	};

	self.removeFile = function () {
		var files = self.activeFiles();

		// AJAX Request

		self.activeFiles([]);
	};
	self.cutFile = function () {
		self.cutFiles(self.activeFiles());
		self.activeFiles([]);
	};
	self.pasteFile = function () {
		var files = self.activeFiles();
		var cutFiles = self.cutFiles();

		// AJAX Request

		self.activeFiles([]);
	};
}