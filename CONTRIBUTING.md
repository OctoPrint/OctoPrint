Issues, Tickets, however you may call them
------------------------------------------

Read the following short instructions **fully** and **follow them** if you want your ticket to be taken care of and not closed again directly! They are linked on top of every new issue form, so don't say nobody warned you afterwards.

- **Read the [FAQ](https://github.com/foosel/OctoPrint/wiki/FAQ)**
- Always create **one ticket for one purpose**. So don't mix two or more feature requests, support requests, bugs etc into one ticket. If you do, your ticket will be closed!
- If you want to report a bug, **READ AND FOLLOW [How to file a bug report](https://github.com/foosel/OctoPrint/wiki/How-to-file-a-bug-report)!** Tickets will be automatically checked if they comply with the requirements outlined in that wiki node! Other then what's written in there (**and really EVERYTHING that is written in there!**) you don't have to do anything special with your ticket. Listen to what GitIssueBot might have to say to you!
- If you want to post a **request** of any kind (feature request, documentation request, ...), **add [Request] to your issue's title!**
- If you need **support** with a problem of your installation (e.g. if you have problems getting the webcam to work) or have a general **question**, the issue tracker is not the right place. Consult the [Mailinglist](https://groups.google.com/group/octoprint) or the [Google+ Community](https://plus.google.com/communities/102771308349328485741) instead!
- If you are a developer that wants to brainstorm a pull request or possible changes to the plugin system, **add [Brainstorming] to your issue's title!** (see below).
- If you have another reason for creating a ticket that doesn't fit any of the above categories, it's something better suited for the [Mailinglist](https://groups.google.com/group/octoprint) or the [Google+ Community](https://plus.google.com/communities/102771308349328485741).

Following these guidelines (**especially EVERYTHING mentioned in ["How to file a bug report"](https://github.com/foosel/OctoPrint/wiki/How-to-file-a-bug-report)**) is necessary so the tickets stay manageable - you are not the only one with an open issue, so please respect that you have to **play by the rules** so that your problem can be taken care of. Tickets not playing by the rules **will be closed without further investigation!**.

Pull Requests
-------------

1. If you want to add a new feature to OctoPrint, **please always first consider if it wouldn't be better suited for a
   plugin.** As a general rule of thumb, any feature that is only of interest to a small sub group should be moved into a
   plugin. If the current plugin system doesn't allow you to implement your feature as a plugin, create a "Brainstorming"
   ticket to get the discussion going how best to solve *this* in OctoPrint's plugin system - maybe that's the actual PR
   you have been waiting for to contribute :)
2. If you plan to make **any large changes to the code or appearance, please open a "Brainstorming" ticket first** so that
   we can determine if it's a good time for your specific pull request. It might be that I'm currently in the process of
   making heavy changes to the code locations you'd target as well, or your approach doesn't fit the general "project
   vision", and that would just cause unnecessary work and frustration for everyone or possibly get the PR rejected.
3. When adding code to OctoPrint, make sure you **follow the current coding style**. That means tabs instead of spaces in the
   python files (yes, I know that this goes against PEP-8, I don't care) and space instead of tabs in the Javascript sources,
   english language (that means code, variables, comments!), comments where necessary (tell why the code does something like
   it does it, structure your code), following the general architecture. If your PR needs to make changes to the Stylesheets,
   change the ``.less`` files from which the CSS is compiled. PRs that contain direct changes to the compiled
   CSS will be closed.
4. **Test your changes thoroughly**. That also means testing with usage scenarios you don't normally use, e.g. if you only
   use access control, test without and vice versa. If you only test with your printer, test with the virtual printer and
   vice versa. State in your pull request how your tested your changes.
5. Please create all pull requests **against the `devel` branch**.
6. Create **one pull request per feature/bug fix**.
7. Create a **custom branch** for your feature/bug fix and use that as base for your pull request. Pull requests directly
   against your version of `devel` will be closed.
8. In your pull request's description, **state what your pull request is doing**, as in, what feature does it implement, what
   bug does it fix. The more thoroughly you explain your intent behind the PR here, the higher the chances it will get merged
   fast.
9. Don't forget to **add yourself to the [AUTHORS](../AUTHORS.md) file** :)

History
-------

  * 2015-01-23: More guidelines for creating pull requests, support/questions redirected to Mailinglist/G+ community
  * 2015-01-27: Added another explicit link to the FAQ
  * 2015-07-07: Added step to add yourself to AUTHORS when creating a PR :)
