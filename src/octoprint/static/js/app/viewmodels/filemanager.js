function FilemanagerViewModel(gcodeFilesViewModel) {
	var self = this;

	self.gcodeFilesViewModel = gcodeFilesViewModel;

	self.directoryContextMenu = $("#dirContextMenu");
	self.fileContextMenu = $("#fileContextMenu");

	$("#directoryTab").on("contextmenu", null, function (e) {
		self.fileContextMenu.hide();
		self.directoryContextMenu.css({ display: "block", left: e.pageX, top: e.pageY });
		return false;
	});
	$("#fileTab").on("contextmenu", null, function (e) {
		self.directoryContextMenu.hide();
		self.fileContextMenu.css({ display: "block", left: e.pageX, top: e.pageY });
		return false;
	});

	$(document).ready(function () {
		$("#name_overlay").on('shown', function () {
			$(this).find("#renameName").focus();
		});
	});

	$(document).click(function () {
		self.directoryContextMenu.hide();
		self.fileContextMenu.hide();
	});

	self.activeFolders = ko.observableArray([]);
	self.copyFolders = ko.observableArray([]);
	self.cutFolders = ko.observableArray([]);

	self.activeFiles = ko.observableArray([]);
	self.copyFiles = ko.observableArray([]);
	self.cutFiles = ko.observableArray([]);

	self.directoryList = ko.observableArray([]);
	self.lastDirectory;

	self.itemList = ko.dependentObservable(function () {
		if (self.activeFolders() == undefined) {
			return [];
		} else {
			var folders = self.activeFolders();
			if (folders.length != 1)
				return [];

			var files = [];
			for (var i = 0; i < folders[0].data.length; i++) {
				if (folders[0].data[i].type == "file")
					files.push(folders[0].data[i]);
			}

			return files;
		}
	});

	self.gcodeFilesViewModel.requestResponse.subscribe(function (response) {
		self.directoryList(response.directories);

		for (var i = 0; i < self.directoryList().length; i++) {
			$("#fm" + self.directoryList()[i].href).click();
		}

		if (self.lastDirectory != undefined) {
			if (!self.selectFolder(self.directoryList()[0].data, self.lastDirectory.relativepath))
				self.selectFolder(self.directoryList()[1].data, self.lastDirectory.relativepath);
		}
	});

	self.displayMode = function (data) {
		if (data.data === undefined)
			return "singleDir";

		var containsDir = false;
		for (var i = 0; !containsDir && i < data.data.length; i++) {
			containsDir = data.data[i].type == "dir";
		}

		return containsDir ? "expandableDir" : "singleDir";
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

	self.selectFolder = function (list, folder) {
		var index = folder.indexOf('/');
		if (index == -1)
			index = folder.indexOf('\\');

		if (index != -1) {
			var subdir = folder.substring(0, index);
			folder = folder.substring(index + 1);

			for (var i = 0; i < list.length; i++) {
				if (list[i].name == subdir) {
					$("#fm" + list[i].href).click();
					return self.selectFolder(list[i].data, folder);
				}
			}
		}
		else {
			for (var i = 0; i < list.length; i++) {
				if (list[i].name == folder) {
					self.activeFolders([list[i]]);
					return true;
				}
			}
		}
		return false;
	};
	self.selectFolderEvent = function (data, e) {
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
	self.selectFileEvent = function (data, e) {
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

	self.enableRemoveFolders = function () {
		var folders = self.activeFolders();
		
		var enabled = true;
		for (var i = 0; enabled && i < folders.length; i++) {
			enabled = self.enableRemoveFolder(folders[i]);
		}

		return enabled;
	}
	self.enableRemoveFolder = function (folder) {
		var enabled = self.enableCopyFolder(folder);

		for (var i = 0; enabled && i < folder.data.Length; i++){
			enabled = self.gcodeFilesViewModel.enableRemove(folder.data[i]);
		}

		return enabled;
	};

	self.enableCopyFolders = function () {
		var folders = self.activeFolders();

		var enabled = true;
		for (var i = 0; enabled && i < folders.length; i++) {
			enabled = self.enableCopyFolder(folders[i]);
		}

		return enabled;
	}
	self.enableCopyFolder = function (folder) {
		var enabled = folder != self.directoryList()[0];
		enabled = enabled && folder != self.directoryList()[1];

		return enabled;
	};

	self.createFolder = function () {
		$("#renameName").val("");
		$("#renameName").keydown(function (e) {
			if (e.keyCode == 13)
			{
				e.preventDefault();
				$("#name_overlay").modal("hide");

				var selectedFolders = self.activeFolders();
				if (selectedFolders.length == 0) {
					for (var i = 0; selectedFolders.length == 0 && i < self.directoryList().length; i++) {
						if (self.directoryList()[i].name == "Uploads")
							selectedFolders = [self.directoryList()[i]];
					}
				}

				var value = $("#renameName").val();
				for (var i = 0; i < selectedFolders.length; i++) {
					var relativePath = selectedFolders[i].relativepath;
					if (relativePath != "")
						relativePath = relativePath + "/";

					$.ajax({
						url: API_BASEURL + "files/" + relativePath + value,
						method: "PUT",
						success: function () { self.gcodeFilesViewModel.requestData(); }
					});
				}
			}
		});
		$("#name_overlay").modal("show");
	};
	self.removeFolder = function () {
		var folders = self.activeFolders();

		for (var i = 0; i < folders.length; i++) {
			if (self.enableRemoveFolder(folders[i]))
				self.gcodeFilesViewModel.removeFile(folders[i]);
		}

		self.activeFolders([]);
	};
	self.copyFolder = function () {
		self.copyFolders(self.activeFolders());
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

	self.enableRemoveFiles = function () {
		var files = self.activeFiles();

		var enabled = true;
		for (var i = 0; enabled && i < files.length; i++) {
			enabled = self.gcodeFilesViewModel.enableRemove(files[i]);
		}

		return enabled;
	}

	self.removeFiles = function () {
		var files = self.activeFiles();

		for (var i = 0; i < files.length; i++) {
			if (self.gcodeFilesViewModel.enableRemove(files[i]))
				self.gcodeFilesViewModel.removeFile(files[i]);
		}

		self.lastDirectory = self.activeFolders()[0];

		self.activeFiles([]);
		self.activeFolders([]);
	};
	self.copyFile = function () {
		self.copyFiles(self.activeFiles());
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