/*!
  Knockout Fast Foreach v0.6.0 (2016-07-28T11:02:54.197Z)
  By: Brian M Hunt (C) 2015 | License: MIT

  Adds `fastForEach` to `ko.bindingHandlers`.
*/
(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define(['knockout'], factory);
  } else if (typeof exports === 'object') {
    module.exports = factory(require('knockout'));
  } else {
    root.KnockoutFastForeach = factory(root.ko);
  }
}(this, function (ko) {
  "use strict";
// index.js
// --------
// Fast For Each
//
// Employing sound techniques to make a faster Knockout foreach binding.
// --------

//      Utilities
var MAX_LIST_SIZE = 9007199254740991;

// from https://github.com/jonschlinkert/is-plain-object
function isPlainObject(o) {
  return !!o && typeof o === 'object' && o.constructor === Object;
}

// From knockout/src/virtualElements.js
var commentNodesHaveTextProperty = document && document.createComment("test").text === "<!--test-->";
var startCommentRegex = commentNodesHaveTextProperty ? /^<!--\s*ko(?:\s+([\s\S]+))?\s*-->$/ : /^\s*ko(?:\s+([\s\S]+))?\s*$/;
var supportsDocumentFragment = document && typeof document.createDocumentFragment === "function";
function isVirtualNode(node) {
  return (node.nodeType === 8) && startCommentRegex.test(commentNodesHaveTextProperty ? node.text : node.nodeValue);
}


// Get a copy of the (possibly virtual) child nodes of the given element,
// put them into a container, then empty the given node.
function makeTemplateNode(sourceNode) {
  var container = document.createElement("div");
  var parentNode;
  if (sourceNode.content) {
    // For e.g. <template> tags
    parentNode = sourceNode.content;
  } else if (sourceNode.tagName === 'SCRIPT') {
    parentNode = document.createElement("div");
    parentNode.innerHTML = sourceNode.text;
  } else {
    // Anything else e.g. <div>
    parentNode = sourceNode;
  }
  ko.utils.arrayForEach(ko.virtualElements.childNodes(parentNode), function (child) {
    // FIXME - This cloneNode could be expensive; we may prefer to iterate over the
    // parentNode children in reverse (so as not to foul the indexes as childNodes are
    // removed from parentNode when inserted into the container)
    if (child) {
      container.insertBefore(child.cloneNode(true), null);
    }
  });
  return container;
}

// Mimic a KO change item 'add'
function valueToChangeAddItem(value, index) {
  return {
    status: 'added',
    value: value,
    index: index
  };
}

// KO 3.4 doesn't seem to export this utility function so it's here just to be sure
function createSymbolOrString(identifier) {
  return typeof Symbol === 'function' ? Symbol(identifier) : identifier;
}

// store a symbol for caching the pending delete info index in the data item objects
var PENDING_DELETE_INDEX_KEY = createSymbolOrString("_ko_ffe_pending_delete_index");

function FastForEach(spec) {
  this.element = spec.element;
  this.container = isVirtualNode(this.element) ?
                   this.element.parentNode : this.element;
  this.$context = spec.$context;
  this.data = spec.data;
  this.as = spec.as;
  this.noContext = spec.noContext;
  this.noIndex = spec.noIndex;
  this.afterAdd = spec.afterAdd;
  this.beforeRemove = spec.beforeRemove;
  this.templateNode = makeTemplateNode(
    spec.templateNode || (spec.name ? document.getElementById(spec.name).cloneNode(true) : spec.element)
  );
  this.afterQueueFlush = spec.afterQueueFlush;
  this.beforeQueueFlush = spec.beforeQueueFlush;
  this.changeQueue = [];
  this.firstLastNodesList = [];
  this.indexesToDelete = [];
  this.rendering_queued = false;
  this.pendingDeletes = [];

  // Remove existing content.
  ko.virtualElements.emptyNode(this.element);

  // Prime content
  var primeData = ko.unwrap(this.data);
  if (primeData.map) {
    this.onArrayChange(primeData.map(valueToChangeAddItem), true);
  }

  // Watch for changes
  if (ko.isObservable(this.data)) {
    if (!this.data.indexOf) {
      // Make sure the observable is trackable.
      this.data = this.data.extend({ trackArrayChanges: true });
    }
    this.changeSubs = this.data.subscribe(this.onArrayChange, this, 'arrayChange');
  }
}

FastForEach.PENDING_DELETE_INDEX_KEY = PENDING_DELETE_INDEX_KEY;

FastForEach.animateFrame = window.requestAnimationFrame || window.webkitRequestAnimationFrame ||
  window.mozRequestAnimationFrame || window.msRequestAnimationFrame ||
  function (cb) { return window.setTimeout(cb, 1000 / 60); };


FastForEach.prototype.dispose = function () {
  if (this.changeSubs) {
    this.changeSubs.dispose();
  }
  this.flushPendingDeletes();
};


// If the array changes we register the change.
FastForEach.prototype.onArrayChange = function (changeSet, isInitial) {
  var self = this;
  var changeMap = {
    added: [],
    deleted: []
  };

  // knockout array change notification index handling:
  // - sends the original array indexes for deletes
  // - sends the new array indexes for adds
  // - sorts them all by index in ascending order
  // because of this, when checking for possible batch additions, any delete can be between to adds with neighboring indexes, so only additions should be checked
  for (var i = 0, len = changeSet.length; i < len; i++) {

    if (changeMap.added.length && changeSet[i].status == 'added') {
      var lastAdd = changeMap.added[changeMap.added.length - 1];
      var lastIndex = lastAdd.isBatch ? lastAdd.index + lastAdd.values.length - 1 : lastAdd.index;
      if (lastIndex + 1 == changeSet[i].index) {
        if (!lastAdd.isBatch) {
          // transform the last addition into a batch addition object
          lastAdd = {
            isBatch: true,
            status: 'added',
            index: lastAdd.index,
            values: [lastAdd.value]
          };
          changeMap.added.splice(changeMap.added.length - 1, 1, lastAdd);
        }
        lastAdd.values.push(changeSet[i].value);
        continue;
      }
    }

    changeMap[changeSet[i].status].push(changeSet[i]);
  }

  if (changeMap.deleted.length > 0) {
    this.changeQueue.push.apply(this.changeQueue, changeMap.deleted);
    this.changeQueue.push({ status: 'clearDeletedIndexes' });
  }
  this.changeQueue.push.apply(this.changeQueue, changeMap.added);
  // Once a change is registered, the ticking count-down starts for the processQueue.
  if (this.changeQueue.length > 0 && !this.rendering_queued) {
    this.rendering_queued = true;
    if (isInitial) {
      self.processQueue();
    } else {
      FastForEach.animateFrame.call(window, function () { self.processQueue(); });
    }
  }
};


// Reflect all the changes in the queue in the DOM, then wipe the queue.
FastForEach.prototype.processQueue = function () {
  var self = this;
  var lowestIndexChanged = MAX_LIST_SIZE;

  // Callback so folks can do things before the queue flush.
  if (typeof this.beforeQueueFlush === 'function') {
    this.beforeQueueFlush(this.changeQueue);
  }

  ko.utils.arrayForEach(this.changeQueue, function (changeItem) {
    if (typeof changeItem.index === 'number') {
      lowestIndexChanged = Math.min(lowestIndexChanged, changeItem.index);
    }
    // console.log(self.data(), "CI", JSON.stringify(changeItem, null, 2), JSON.stringify($(self.element).text()))
    self[changeItem.status](changeItem);
    // console.log("  ==> ", JSON.stringify($(self.element).text()))
  });
  this.flushPendingDeletes();
  this.rendering_queued = false;

  // Update our indexes.
  if (!this.noIndex) {
    this.updateIndexes(lowestIndexChanged);
  }

  // Callback so folks can do things.
  if (typeof this.afterQueueFlush === 'function') {
    this.afterQueueFlush(this.changeQueue);
  }
  this.changeQueue = [];
};


function extendWithIndex(context) {
  context.$index = ko.observable();
};


// Process a changeItem with {status: 'added', ...}
FastForEach.prototype.added = function (changeItem) {
  var index = changeItem.index;
  var valuesToAdd = changeItem.isBatch ? changeItem.values : [changeItem.value];
  var referenceElement = this.getLastNodeBeforeIndex(index);
  // gather all childnodes for a possible batch insertion
  var allChildNodes = [];

  for (var i = 0, len = valuesToAdd.length; i < len; ++i) {
    var childNodes;

    // we check if we have a pending delete with reusable nodesets for this data, and if yes, we reuse one nodeset
    var pendingDelete = this.getPendingDeleteFor(valuesToAdd[i]);
    if (pendingDelete && pendingDelete.nodesets.length) {
      childNodes = pendingDelete.nodesets.pop();
    } else {
      var templateClone = this.templateNode.cloneNode(true);
      var childContext;

      if (this.noContext) {
        childContext = this.$context.extend({
          $item: valuesToAdd[i],
          $index: this.noIndex ? undefined : ko.observable()
        });
      } else {
        childContext = this.$context.createChildContext(valuesToAdd[i], this.as || null, this.noIndex ? undefined : extendWithIndex);
      }

      // apply bindings first, and then process child nodes, because bindings can add childnodes
      ko.applyBindingsToDescendants(childContext, templateClone);

      childNodes = ko.virtualElements.childNodes(templateClone);
    }

    // Note discussion at https://github.com/angular/angular.js/issues/7851
    allChildNodes.push.apply(allChildNodes, Array.prototype.slice.call(childNodes));
    this.firstLastNodesList.splice(index + i, 0, { first: childNodes[0], last: childNodes[childNodes.length - 1] });
  }

  if (typeof this.afterAdd === 'function') {
    this.afterAdd({
      nodeOrArrayInserted: this.insertAllAfter(allChildNodes, referenceElement),
      foreachInstance: this
    }
    );
  } else {
    this.insertAllAfter(allChildNodes, referenceElement);
  }
};

FastForEach.prototype.getNodesForIndex = function (index) {
  var result = [],
    ptr = this.firstLastNodesList[index].first,
    last = this.firstLastNodesList[index].last;
  result.push(ptr);
  while (ptr && ptr !== last) {
    ptr = ptr.nextSibling;
    result.push(ptr);
  }
  return result;
};

FastForEach.prototype.getLastNodeBeforeIndex = function (index) {
  if (index < 1 || index - 1 >= this.firstLastNodesList.length)
    return null;
  return this.firstLastNodesList[index - 1].last;
};

FastForEach.prototype.insertAllAfter = function (nodeOrNodeArrayToInsert, insertAfterNode) {
  var frag, len, i,
    containerNode = this.element;

  // poor man's node and array check, should be enough for this
  if (nodeOrNodeArrayToInsert.nodeType === undefined && nodeOrNodeArrayToInsert.length === undefined) {
    throw new Error("Expected a single node or a node array");
  }
  if (nodeOrNodeArrayToInsert.nodeType !== undefined) {
    ko.virtualElements.insertAfter(containerNode, nodeOrNodeArrayToInsert, insertAfterNode);
    return [nodeOrNodeArrayToInsert];
  } else if (nodeOrNodeArrayToInsert.length === 1) {
    ko.virtualElements.insertAfter(containerNode, nodeOrNodeArrayToInsert[0], insertAfterNode);
  } else if (supportsDocumentFragment) {
    frag = document.createDocumentFragment();

    for (i = 0, len = nodeOrNodeArrayToInsert.length; i !== len; ++i) {
      frag.appendChild(nodeOrNodeArrayToInsert[i]);
    }
    ko.virtualElements.insertAfter(containerNode, frag, insertAfterNode);
  } else {
    // Nodes are inserted in reverse order - pushed down immediately after
    // the last node for the previous item or as the first node of element.
    for (i = nodeOrNodeArrayToInsert.length - 1; i >= 0; --i) {
      var child = nodeOrNodeArrayToInsert[i];
      if (!child) { break; }
      ko.virtualElements.insertAfter(containerNode, child, insertAfterNode);
    }
  }
  return nodeOrNodeArrayToInsert;
};

// checks if the deleted data item should be handled with delay for a possible reuse at additions
FastForEach.prototype.shouldDelayDeletion = function (data) {
  return data && (typeof data === "object" || typeof data === "function");
};

// gets the pending deletion info for this data item
FastForEach.prototype.getPendingDeleteFor = function (data) {
  var index = data && data[PENDING_DELETE_INDEX_KEY];
  if (index === undefined) return null;
  return this.pendingDeletes[index];
};

// tries to find the existing pending delete info for this data item, and if it can't, it registeres one
FastForEach.prototype.getOrCreatePendingDeleteFor = function (data) {
  var pd = this.getPendingDeleteFor(data);
  if (pd) {
    return pd;
  }
  pd = {
    data: data,
    nodesets: []
  };
  data[PENDING_DELETE_INDEX_KEY] = this.pendingDeletes.length;
  this.pendingDeletes.push(pd);
  return pd;
};

// Process a changeItem with {status: 'deleted', ...}
FastForEach.prototype.deleted = function (changeItem) {
  // if we should delay the deletion of this data, we add the nodeset to the pending delete info object
  if (this.shouldDelayDeletion(changeItem.value)) {
    var pd = this.getOrCreatePendingDeleteFor(changeItem.value);
    pd.nodesets.push(this.getNodesForIndex(changeItem.index));
  } else { // simple data, just remove the nodes
    this.removeNodes(this.getNodesForIndex(changeItem.index));
  }
  this.indexesToDelete.push(changeItem.index);
};

// removes a set of nodes from the DOM
FastForEach.prototype.removeNodes = function (nodes) {
  if (!nodes.length) { return; }

  var removeFn = function () {
    var parent = nodes[0].parentNode;
    for (var i = nodes.length - 1; i >= 0; --i) {
      ko.cleanNode(nodes[i]);
      parent.removeChild(nodes[i]);
    }
  };

  if (this.beforeRemove) {
    var beforeRemoveReturn = this.beforeRemove({
      nodesToRemove: nodes, foreachInstance: this
    }) || {};
    // If beforeRemove returns a `then`–able e.g. a Promise, we remove
    // the nodes when that thenable completes.  We pass any errors to
    // ko.onError.
    if (typeof beforeRemoveReturn.then === 'function') {
      beforeRemoveReturn.then(removeFn, ko.onError ? ko.onError : undefined);
    }
  } else {
    removeFn();
  }
};

// flushes the pending delete info store
// this should be called after queue processing has finished, so that data items and remaining (not reused) nodesets get cleaned up
// we also call it on dispose not to leave any mess
FastForEach.prototype.flushPendingDeletes = function () {
  for (var i = 0, len = this.pendingDeletes.length; i != len; ++i) {
    var pd = this.pendingDeletes[i];
    while (pd.nodesets.length) {
      this.removeNodes(pd.nodesets.pop());
    }
    if (pd.data && pd.data[PENDING_DELETE_INDEX_KEY] !== undefined)
      delete pd.data[PENDING_DELETE_INDEX_KEY];
  }
  this.pendingDeletes = [];
};

// We batch our deletion of item indexes in our parallel array.
// See brianmhunt/knockout-fast-foreach#6/#8
FastForEach.prototype.clearDeletedIndexes = function () {
  // We iterate in reverse on the presumption (following the unit tests) that KO's diff engine
  // processes diffs (esp. deletes) monotonically ascending i.e. from index 0 -> N.
  for (var i = this.indexesToDelete.length - 1; i >= 0; --i) {
    this.firstLastNodesList.splice(this.indexesToDelete[i], 1);
  }
  this.indexesToDelete = [];
};


FastForEach.prototype.getContextStartingFrom = function (node) {
  var ctx;
  while (node) {
    ctx = ko.contextFor(node);
    if (ctx) { return ctx; }
    node = node.nextSibling;
  }
};


FastForEach.prototype.updateIndexes = function (fromIndex) {
  var ctx;
  for (var i = fromIndex, len = this.firstLastNodesList.length; i < len; ++i) {
    ctx = this.getContextStartingFrom(this.firstLastNodesList[i].first);
    if (ctx) { ctx.$index(i); }
  }
};


ko.bindingHandlers.fastForEach = {
  // Valid valueAccessors:
  //    []
  //    ko.observable([])
  //    ko.observableArray([])
  //    ko.computed
  //    {data: array, name: string, as: string}
  init: function init(element, valueAccessor, bindings, vm, context) {
    var ffe, value = valueAccessor();
    if (isPlainObject(value)) {
      value.element = value.element || element;
      value.$context = context;
      ffe = new FastForEach(value);
    } else {
      ffe = new FastForEach({
        element: element,
        data: ko.unwrap(context.$rawData) === value ? context.$rawData : value,
        $context: context
      });
    }

    ko.utils.domNodeDisposal.addDisposeCallback(element, function () {
      ffe.dispose();
    });
    return { controlsDescendantBindings: true };
  },

  // Export for testing, debugging, and overloading.
  FastForEach: FastForEach
};

ko.virtualElements.allowedBindings.fastForEach = true;
}));