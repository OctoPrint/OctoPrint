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
			if (folders.length == 0 || folders.length != 1)
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

			if (self.lastDirectory.relativepath == "")
				self.selectFolder(self.directoryList(), "Uploads");

			self.lastDirectory = undefined;
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

		return _.indexOf(self.activeFolders(), data) != -1;
	};
	self.isFolderCut = function (data) {
		if (data === undefined || self.cutFolders() === undefined)
			return false;

		return _.indexOf(self.cutFolders(), data.relativepath) != -1;
	};

	self.isFileSelected = function (data) {
		if (data === undefined || self.activeFiles() === undefined)
			return false;

		return _.indexOf(self.activeFiles(), data) != -1;
	};
	self.isFileCut = function (data) {
		if (data === undefined || self.cutFiles() === undefined)
			return false;

		return _.indexOf(self.cutFiles(), data.relativepath) != -1;
	};

	self.selectFolder = function (list, folder) {
		var index = folder.indexOf('/');
		if (index == -1)
			index = folder.indexOf('\\');

		if (index != -1) {
			var subdir = folder.substring(0, index);
			folder = folder.substring(index + 1);

			var obj = _.chain(list).filter(function (v) { return v.name == subdir; }).first().value();
			$("#fm" + obj.href).click();
			return self.selectFolder(obj.data, folder);
		}
		else 
			self.activeFolders(_.chain(list).filter(function (v) { return v.name == folder; }).value());

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
				e.stopPropagation();

				$("#name_overlay").modal("hide");

				var selectedFolders = self.activeFolders().map(function (v) { return v.relativepath; });
				if (selectedFolders.length == 0) {
					selectedFolders = [""];
				}

				var value = $("#renameName").val();
				var folders = _.chain(selectedFolders).map(function (v) { return v == "" ? value : v + "/" + value; }).value();

				$.ajax({
					url: API_BASEURL + "files/command",
					method: "POST",
					dataType: "json",
					contentType: "application/json; charset=UTF-8",
					data: JSON.stringify({ "command": "create", "type": "dir", "targets": folders }),
					success: function () { self.gcodeFilesViewModel.requestData(); }
				});
			}
		});
		$("#name_overlay").modal("show");
	};
	self.removeFolder = function () {
		var folders = _.chain(self.activeFolders()).filter(function (v) { return self.enableRemoveFolder(v); }).map(function (v) { return v.relativepath; }).value();

		$.ajax({
			url: API_BASEURL + "files/command",
			method: "POST",
			dataType: "json",
			contentType: "application/json; charset=UTF-8",
			data: JSON.stringify({ "command": "delete", "type": "dir", "targets": folders }),
			success: function () { self.gcodeFilesViewModel.requestData(); }
		});

		self.lastDirectory = self.activeFolders()[0];
		self.activeFolders([]);
	};
	self.copyFolder = function () {
		self.copyFolders(self.activeFolders().map(function(v) { return v.relativepath; }));
	};
	self.cutFolder = function () {
		self.cutFolders(self.activeFolders().map(function (v) { return v.relativepath; }));
	};
	self.pasteFolder = function () {
		var folders = self.activeFolders().map(function (v) { return v.relativepath; });
		var copyFolders = self.copyFolders();
		var cutFolders = self.cutFolders();

		if (copyFolders.length > 0) {
			$.ajax({
				url: API_BASEURL + "files/command",
				method: "POST",
				dataType: "json",
				contentType: "application/json; charset=UTF-8",
				data: JSON.stringify({ "command": "copy", "type": "dir", "targets": copyFolders, "destinations": folders }),
				success: function () { self.gcodeFilesViewModel.requestData(); }
			});
		}
		if (cutFolders.length > 0) {
			$.ajax({
				url: API_BASEURL + "files/command",
				method: "POST",
				dataType: "json",
				contentType: "application/json; charset=UTF-8",
				data: JSON.stringify({ "command": "cut", "type": "dir", "targets": cutFolders, "destinations": folders }),
				success: function () { self.gcodeFilesViewModel.requestData(); }
			});
		}

		self.lastDirectory = self.activeFolders()[0];
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
		self.copyFiles(self.activeFiles().map(function (v) { return v.relativepath; }));
	};
	self.cutFile = function () {
		self.cutFiles(self.activeFiles().map(function (v) { return v.relativepath; }));
	};
	self.pasteFile = function () {
		var folders = self.activeFolders().map(function (v) { return v.relativepath; });
		var copyFiles = self.copyFiles();
		var cutFiles = self.cutFiles();

		if (copyFiles.length > 0) {
			$.ajax({
				url: API_BASEURL + "files/command",
				method: "POST",
				dataType: "json",
				contentType: "application/json; charset=UTF-8",
				data: JSON.stringify({ "command": "copy", "type": "file", "targets": copyFiles, "destinations": folders }),
				success: function () { self.gcodeFilesViewModel.requestData(); }
			});
		}
		if (cutFiles.length > 0) {
			$.ajax({
				url: API_BASEURL + "files/command",
				method: "POST",
				dataType: "json",
				contentType: "application/json; charset=UTF-8",
				data: JSON.stringify({ "command": "cut", "type": "file", "targets": cutFiles, "destinations": folders }),
				success: function () { self.gcodeFilesViewModel.requestData(); }
			});
		}

		self.lastDirectory = self.activeFolders()[0];

		self.activeFiles([]);
		self.activeFolders([]);
	};
}