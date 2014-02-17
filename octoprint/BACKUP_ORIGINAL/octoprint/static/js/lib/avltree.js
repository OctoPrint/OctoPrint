// AVLTree ///////////////////////////////////////////////////////////////////
//   self file is originally from the Concentré XML project (version 0.2.1)
//   Licensed under GPL and LGPL
//
//   Modified by Jeremy Stephens.
//
//   Taken from: https://gist.github.com/viking/2424106, modified to not only use string literals when searching

// Pass in the attribute you want to use for comparing
function AVLTree(n, attr) {
    var self = this;

    self.attr = attr;
    self.left = null;
    self.right = null;
    self.node = n;
    self.depth = 1;
    self.elements = [n];

    self.balance = function() {
        var ldepth = self.left  == null ? 0 : self.left.depth;
        var rdepth = self.right == null ? 0 : self.right.depth;

        if (ldepth > rdepth + 1) {
            // LR or LL rotation
            var lldepth = self.left.left  == null ? 0 : self.left.left.depth;
            var lrdepth = self.left.right == null ? 0 : self.left.right.depth;

            if (lldepth < lrdepth) {
                // LR rotation consists of a RR rotation of the left child
                self.left.rotateRR();
                // plus a LL rotation of self node, which happens anyway
            }
            self.rotateLL();
        } else if (ldepth + 1 < rdepth) {
            // RR or RL rorarion
            var rrdepth = self.right.right == null ? 0 : self.right.right.depth;
            var rldepth = self.right.left  == null ? 0 : self.right.left.depth;

            if (rldepth > rrdepth) {
                // RR rotation consists of a LL rotation of the right child
                self.right.rotateLL();
                // plus a RR rotation of self node, which happens anyway
            }
            self.rotateRR();
        }
    }
    
    self.rotateLL = function() {
        // the left side is too long => rotate from the left (_not_ leftwards)
        var nodeBefore = self.node;
        var elementsBefore = self.elements;
        var rightBefore = self.right;
        self.node = self.left.node;
        self.elements = self.left.elements;
        self.right = self.left;
        self.left = self.left.left;
        self.right.left = self.right.right;
        self.right.right = rightBefore;
        self.right.node = nodeBefore;
        self.right.elements = elementsBefore;
        self.right.updateInNewLocation();
        self.updateInNewLocation();
    }
    
    self.rotateRR = function() {
        // the right side is too long => rotate from the right (_not_ rightwards)
        var nodeBefore = self.node;
        var elementsBefore = self.elements;
        var leftBefore = self.left;
        self.node = self.right.node;
        self.elements = self.right.elements;
        self.left = self.right;
        self.right = self.right.right;
        self.left.right = self.left.left;
        self.left.left = leftBefore;
        self.left.node = nodeBefore;
        self.left.elements = elementsBefore;
        self.left.updateInNewLocation();
        self.updateInNewLocation();
    }
    
    self.updateInNewLocation = function() {
        self.getDepthFromChildren();
    }
    
    self.getDepthFromChildren = function() {
        self.depth = self.node == null ? 0 : 1;
        if (self.left != null) {
            self.depth = self.left.depth + 1;
        }
        if (self.right != null && self.depth <= self.right.depth) {
            self.depth = self.right.depth + 1;
        }
    }
    
    self.compare = function(n1, n2) {
        var v1 = n1[self.attr];
        var v2 = n2[self.attr];
        if (v1 == v2) {
            return 0;
        }
        if (v1 < v2) {
            return -1;
        }
        return 1;
    }
    
    self.add = function(n) {
        var o = self.compare(n, self.node);
        if (o == 0) {
            self.elements.push(n);
            return false;
        }

        var ret = false;
        if (o == -1) {
            if (self.left == null) {
                self.left = new AVLTree(n, self.attr);
                ret = true;
            } else {
                ret = self.left.add(n);
                if (ret) {
                    self.balance();
                }
            }
        } else if (o == 1) {
            if (self.right == null) {
                self.right = new AVLTree(n, self.attr);
                ret = true;
            } else {
                ret = self.right.add(n);
                if (ret) {
                    self.balance();
                }
            }
        }

        if (ret) {
            self.getDepthFromChildren();
        }
        return ret;
    }
    
    self.findBest = function(value) {
        if (value < self.node[self.attr]) {
            if (self.left != null) {
                return self.left.findBest(value);
            }
        } else if (value > self.node[self.attr]) {
            if (self.right != null) {
                return self.right.findBest(value);
            }
        }

        return self.elements;
    }
    
    self.find = function(value) {
        var elements = self.findBest(value);
        for (var i = 0; i < elements.length; i++) {
            if (elements[i][self.attr] == value) {
                return elements;
            }
        }

        return false;
    }
}
