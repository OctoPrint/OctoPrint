function DialogsViewModel() {
	var self = this;

	self.name = ko.observable("");
	self.type = ko.observable("command");
	self.commands = ko.observable("");

	// Parametric
	self.inputs = ko.observableArray([]);

	// Feedback
	self.template = ko.observable("");
	self.regex = ko.observable("");

	self.removeInput = function (data) {
		self.inputs.remove(data);
	};

	self.addInput = function () {
		self.inputs.push({ name: "", parameter: "", defaultValue: "" });
	};
}