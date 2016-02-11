/**
 * Babel JavaScript Support
 *
 * Copyright (C) 2008-2011 Edgewall Software
 * All rights reserved.
 *
 * This software is licensed as described in the file COPYING, which
 * you should have received as part of this distribution. The terms
 * are also available at http://babel.edgewall.org/wiki/License.
 *
 * This software consists of voluntary contributions made by many
 * individuals. For the exact contribution history, see the revision
 * history and logs, available at http://babel.edgewall.org/log/.
 */

/**
 * A simple module that provides a gettext like translation interface.
 * The catalog passed to load() must be a object conforming to this
 * interface::
 *
 *    {
 *      messages:     an object of {msgid: translations} items where
 *                    translations is an array of messages or a single
 *                    string if the message is not pluralizable.
 *      plural_expr:  the plural expression for the language.
 *      locale:       the identifier for this locale.
 *      domain:       the name of the domain.
 *    }
 *
 * Missing elements in the object are ignored.
 *
 * Typical usage::
 *
 *    var translations = babel.Translations.load(...).install();
 */
var babel = new function() {

  var defaultPluralExpr = function(n) { return n == 1 ? 0 : 1; };
  var formatRegex = /%?%(?:\(([^\)]+)\))?([disr])/g;

  /**
   * A translations object implementing the gettext interface
   */
  var Translations = this.Translations = function(locale, domain) {
    this.messages = {};
    this.locale = locale || 'unknown';
    this.domain = domain || 'messages';
    this.pluralexpr = defaultPluralExpr;
  };

  /**
   * Create a new translations object from the catalog and return it.
   * See the babel-module comment for more details.
   */
  Translations.load = function(catalog) {
    var rv = new Translations();
    rv.load(catalog);
    return rv;
  };

  Translations.prototype = {
    /**
     * translate a single string.
     */
    gettext: function(string) {
      var translated = this.messages[string];
      if (typeof translated == 'undefined')
        return string;
      return (typeof translated == 'string') ? translated : translated[0];
    },

    /**
     * translate a pluralizable string
     */
    ngettext: function(singular, plural, n) {
      var translated = this.messages[singular];
      if (typeof translated == 'undefined')
        return (n == 1) ? singular : plural;
      return translated[this.pluralexpr(n)];
    },

    /**
     * Install this translation document wide.  After this call, there are
     * three new methods on the window object: _, gettext and ngettext
     */
    install: function() {
      var self = this;
      window.gettext = function(string) {
        return self.gettext(string);
      };
      window.ngettext = function(singular, plural, n) {
        return self.ngettext(singular, plural, n);
      };
      return this;
    },

    /**
     * Works like Translations.load but updates the instance rather
     * then creating a new one.
     */
    load: function(catalog) {
      if (catalog.messages)
        this.update(catalog.messages);
      if (catalog.plural_expr)
        this.setPluralExpr(catalog.plural_expr);
      if (catalog.locale)
        this.locale = catalog.locale;
      if (catalog.domain)
        this.domain = catalog.domain;
      return this;
    },

    /**
     * Updates the translations with the object of messages.
     */
    update: function(mapping) {
      for (var key in mapping)
        if (mapping.hasOwnProperty(key))
          this.messages[key] = mapping[key];
      return this;
    },

    /**
     * Sets the plural expression
     */
    setPluralExpr: function(expr) {
      this.pluralexpr = new Function('n', 'return +(' + expr + ')');
      return this;
    }
  };

  /**
   * A python inspired string formatting function.  Supports named and
   * positional placeholders and "s", "d" and "i" as type characters
   * without any formatting specifications.
   *
   * Examples::
   *
   *    babel.format(_('Hello %s'), name)
   *    babel.format(_('Progress: %(percent)s%%'), {percent: 100})
   */ 
  this.format = function() {
    var arg, string = arguments[0], idx = 0;
    if (arguments.length == 1)
      return string;
    else if (arguments.length == 2 && typeof arguments[1] == 'object')
      arg = arguments[1];
    else {
      arg = [];
      for (var i = 1, n = arguments.length; i != n; ++i)
        arg[i - 1] = arguments[i];
    }
    return string.replace(formatRegex, function(all, name, type) {
      if (all[0] == all[1]) return all.substring(1);
      var value = arg[name || idx++];
      return (type == 'i' || type == 'd') ? +value : value; 
    });
  }

};
