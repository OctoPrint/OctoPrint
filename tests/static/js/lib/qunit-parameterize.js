/*
 * Parameterize v 0.4
 * A QUnit Addon For Running Parameterized Tests
 * https://github.com/AStepaniuk/qunit-parameterize
 * Released under the MIT license. 
 */
QUnit.extend(QUnit, {
	cases : function(testCases) {
		var currentCases = testCases;

		var createTest = function(methodName, title, expected, callback, parameters) {
			QUnit[methodName](
				title,
				expected,
				function(assert) { return callback.call(this, parameters, assert); }
			);
		};

		var iterateTestCases = function(methodName, title, expected, callback) {
			if (!currentCases || currentCases.length == 0) {
				// setup test which will always fail
				QUnit.test(title, function(assert) {
					assert.ok(false, "No test cases are provided");
				});
				return;
			}

			if (!callback) {
				callback = expected;
				expected = null;
			}

			for (var i = 0; i < currentCases.length; ++i) {
				var parameters = currentCases[i];

				var testCaseTitle = title;
				if (parameters.title) {
					testCaseTitle += "[" + parameters.title + "]"; 
				}

				createTest(methodName, testCaseTitle, expected, callback, parameters);
			}
		}

		var getLength = function(arr) {
			return arr ? arr.length : 0;
		}

		var getItem = function(arr, idx) {
			return arr ? arr[idx] : undefined;
		}
		
		var mix = function(testCase, mixData) {
			if (testCase && mixData) {
				var result = clone(testCase);
				for(var p in mixData) {
					if (p !== "title") {
						if (!(p in result))  result[p] = mixData[p];
					} else {
						result[p] = [result[p], mixData[p]].join("");
					}
				}
				return result;
			} else if (testCase) {
				return testCase;
			} else if (mixData) {
				return mixData;
			} else {
				// return null or undefined whatever testCase is
				return testCase;
			}
		}

		var clone = function(testCase) {
			var result = {};
			for (var p in testCase) {
				result[p] = testCase[p];
			}
			return result;
		}

		return {
			sequential : function(addData) {
				var casesLength = getLength(currentCases);
				var addDataLength = getLength(addData);
				var length = casesLength > addDataLength ? casesLength : addDataLength;

				var newCases = [];
				for (var i = 0; i < length; ++i) {
					var currentCaseI = getItem(currentCases, i);
					var dataI = getItem(addData, i);
					var newCase = mix(currentCaseI, dataI);

					if (newCase) newCases.push(newCase);
				}
				currentCases = newCases;

				return this;
			},

			combinatorial : function(mixData) {
				var current = (currentCases && currentCases.length > 0) ? currentCases : [ null ];
				mixData = (mixData && mixData.length > 0) ? mixData : [ null ];
				var currentLength = current.length;
				var mixDataLength = mixData.length;

				var newCases = [];
				for (var i = 0; i < currentLength; ++i) {
					for(var j = 0; j < mixDataLength; ++j) {
						var currentCaseI = current[i];
						var dataJ = mixData[j];
						var newCase = mix(currentCaseI, dataJ);

						if (newCase) newCases.push(newCase);
					}
				}
				currentCases = newCases;

				return this;
			},

			test : function(title, expected, callback) {
				iterateTestCases("test", title, expected, callback);
				return this;
			},

			asyncTest : function(title, expected, callback) {
				iterateTestCases("asyncTest", title, expected, callback);
				return this;
			}
		}
	}
});
