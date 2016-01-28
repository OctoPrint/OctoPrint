.. _sec-configuration-yaml:

A YAML Primer
=============

Most of OctoPrint's configuration is done under the hood through `YAML <https://en.wikipedia.org/wiki/YAML>`_ files,
which is why it makes sense to shed some light on the basics of this data serialization format.

YAML is a text based format which excels at representing the most common of data structures in an easy and very human
readable way, which is why it was chosen for OctoPrint's configuration files. A text editor is all you need in order
to write YAML configuration files.

.. _sec-configuration-yaml-basic:

Basic Rules
-----------

First of all some basic things to know about working with YAML files:

  * Never use tabs outside of quoted strings, especially not for indentation. The tab character is illegal within
    YAML files.
  * Whitespace and indentation matters and plays an important part in structuring the data, so take special care
    to stay consistent here.
  * YAML's comments start with a ``#`` and go until the end of the line.

.. _sec-configuration-yaml-types:

Interesting data types
----------------------

You will probably only come across the three most basic types of data within OctoPrint's YAML files: scalars
(such as strings, integers, ...), lists and associated arrays (aka key-value-pairs, aka maps, aka dictionaries).

.. _sec-configuration-yaml-types-scalar:

Scalars
.......

Scalars are the most basic of all data types and are simple string, integer, float or boolean values.

For most scalars you don't need any quotes at all, but if you need to define some piece of data which contains characters
that could be mistaken with YAML syntax you need to quote it in either double ``"`` or single ``'`` quotes for the
YAML file to stay valid. As simple rule of thumb, if your data contains any of these characters ``:-{}[]!#|>&%@`` better
quote it. Also quote it if you want a string but it could be mistaken for a valid number (integer or float) or if
it consists only of "Yes", "No", "yes", "no", "true" or "false", which would be converted to a boolean without quotes.

In double quoted strings if you need to include a literal double quote in your string you can escape it by prefixing
it with a backslash ``\`` (which you can in turn escape by itself). In single quoted strings the single quote character
can be escaped by prefixing it with another single quote, basically doubling it. Backslashes in single quoted strings
do not need to be escaped.

Quoted strings can also span across multiple lines, just indent the following lines. Note that you'll need to add a
completely empty line in order for force a line break, the data will not be actually wrapped across multiple lines
just because you spread its representation across multiple lines.

.. _sec-configuration-yaml-types-scalar-int:

int
'''

.. code-block:: yaml

   23

   42

.. _sec-configuration-yaml-types-scalar-float:

float
'''''

.. code-block:: yaml

   23.5

   100.0

.. _sec-configuration-yaml-types-scalar-boolean:

boolean
'''''''

.. code-block:: yaml

   true

   false

   Yes

   No

   yes

   no

.. _sec-configuration-yaml-types-scalar-string:

string
''''''

.. code-block:: yaml

   a string

   "some quoted string with a : colon and a { bracket and a quote \" and a backslash \\ - phew"

   'some single quoted string with a single quote '' and a backslash \ - yay'

   "and a multiline string - just because we can we'll make it span
     across not two but four YAML lines!

     Including this paragraph. But in fact it will only be two lines :)"

   "23"

   "42.3"

   "Yes"

   "No"

   "true"

   "false"

   yes and no

   true or false

.. _sec-configuration-yaml-types-lists:

Lists
.....

Lists allow to "collect" a number of similar things into one data structure. They are created by prefixing one or more
consecutive lines with a ``-``:

.. code-block:: yaml

   - item 1
   - 23.42
   - 57
   - true

Take special care to have all of your list items at the same indentation level!

.. _sec-configuration-yaml-types-dicts:

Dictionaries
............

Dictionaries (aka associative arrays aka maps) allow organizing the data in key value pairs, with the key and the value
being separated through a colon ``:``:

.. sourcecode:: yaml

   key: value
   anotherkey: another value

.. _sec-configuration-yaml-examples:

Examples
--------

Based on the three types explained above, quite complex data structures are possible (whitespace made visible to
help track indentation):

.. code-block-ext:: yaml
   :whitespace:

   general:
     some_setting: some_value
     a_list:
     - item 1
     - 23.42
     - 57
     - true
     some_flag: true
     quoted_string: "This string is quoted because {we have this here} and also > this and : that"
   specific:
     setting1: value1
     setting2:
       subsetting21: value11
       subsetting22:
       - subsubsetting221
       - subsubsetting222
       - subsubsetting223
   the_end: yes

In this example we have a dictionary on the top most "layer" which has three keys, ``general``, ``specific`` and
``the_end``.

``general`` in turn is a dictionary with the keys ``some_setting`` (a string), ``a_list`` (a list with four items,
a string, a float, an int and a boolean), ``some_flag`` (a boolean) and ``quoted_string`` (a -- you guessed it -- string).

``specific`` is also a dictionary, with keys ``setting1`` (a string) and ``setting2``, a dictionary with two keys, one
a string and the other again a list.

Finally, ``the_end`` is just a boolean, since an unquoted ``yes`` evaluates as a boolean value as we saw in the
:ref:`section about boolean scalars above <sec-configuration-yaml-types-scalar-boolean>`.

Don't get confused by the list "dividing" one part of the dictionary under ``general`` from the other -- your mind is
just playing a trick on you due to the list's dashes ``-`` being on the same levels as the dictionary keys. You could
also just add two more spaces to your indentation and write that part like this, which makes the structure a bit
clearer (whitespace again made visible to help track indentation):

.. code-block-ext:: yaml
   :whitespace:

   general:
       some_setting: some_value
       a_list:
         - item 1
         - 23.42
         - 57
         - true
       some_flag: true
   # ...

Just make sure you follow a consistent way of indenting your files -- YAML is not as strict as Python when it comes to
differing indentation variants within the same file (as long as it's still valid), but consistency will help you as
a lot as a human. Ideally you'll use a text editor which highlights white space characters for you (most editors can
be configured this way), this will help tremendously when editing whitespace sensitive syntax such as YAML.