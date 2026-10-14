***The canonical URL for OctoPrint's security policy is https://octoprint.org/security/ - its contents are copied here for convenience.***

<!--
> [!WARNING]
> **OctoPrint is participating in the [Summer of Bliss](https://daniel.haxx.se/blog/2026/06/15/curl-summer-of-bliss/) and will not be processing any security reports between July 10th & August 23rd 2026**. Any reports sent during this time will get processed from August 24th onward. This also extends the reaction & mitigation times accordingly.
>
> OctoPrint's maintainer needs a vacation too.
-->

**If you think that you have found a security vulnerability in OctoPrint, please disclose it to us via a [GitHub Security Advisory (GHSA)](https://github.com/OctoPrint/OctoPrint/security/advisories) or alternatively our security e-mail address at [security@octoprint.org](mailto:security@octoprint.org)**.

We are mostly interested in reports by actual OctoPrint users that are familiar with the platform, but all high quality contributions are welcome. Please do your best to describe a clear and realistic impact for your report.

If you are going to write about OctoPrint's security, please get in touch, so we can make sure that all claims are correct.

## Reaction & mitigation times

For the sake of OctoPrint's user base, **do not make vulnerabilities public without notifying us and giving us at least 90 days to release a fixed version**. This includes not posting a vulnerability report to the project's issue tracker, the forums or any other public place.

We will do our best to respond to your report within 7 days, and also to keep you informed of the progress of our efforts to resolve the issue, but understand that OctoPrint like many Open Source projects is primarily a volunteer project with only one full-time resource, and we may not be able to respond as quickly as you would like due to other responsibilities.

## Supported versions

We only accept reports against the latest stable & official version of OctoPrint or any versions beyond that currently in development (`dev`, `next`, `bugfix` branches on the Git repository). The latest version can be found [here](https://github.com/OctoPrint/OctoPrint/releases/latest).

We do not accept reports against forks of OctoPrint.

## Non-qualifying vulnerabilities

We will not accept reports of vulnerabilities of the following types:

- Theoretical attacks without proof of exploitability
- Attacks that are located within a third party library (these should instead be reported to the library maintainers)
- Attacks that require the user to have severely misconfigured their OctoPrint instance or any reverse proxies in front of it
- Attacks that require admin access to the OctoPrint instance (this includes but is not limited to: configuring malicious commands, installing malicious plugins or language packs)
- Attacks that require social engineering to succeed (the user can only perform them on themselves and must get actively involved, e.g. causing a severe misconfiguration)
- Attacks involving physical access to a user's device, or involving a device or network that's already severely compromised (eg man-in-the-middle, compromised SSH access, ...).
- Attacks that require the user to expose their OctoPrint instance on the public internet or another hostile network

## On the use of AI

If AI is used to generate any portion of the vulnerability report, contributors must adhere to the following requirements:

1. Explicitly disclose the manner in which AI was employed: what tools where used, in which steps where they used, ...
2. Double-check the findings carefully before reporting them to us to validate that the issues are indeed existing and working exactly as the AI says. AI-based tools frequently generate inaccurate or fabricated results.
3. Be prepared to share the used prompts.

Further: It is rarely a good idea to just copy and paste an AI generated report to the project. Those generated reports typically are too wordy and rarely to the point (in addition to the common fabricated details). If you actually find a problem with an AI and you have verified it yourself to be true: Write the report yourself and explain the problem as you have verified it. This makes sure the AI-generated inaccuracies and invented issues are filtered out early before they waste more people's time.

As we take security reports seriously, we investigate each report with priority. This work is both time and energy consuming and pulls us away from doing other meaningful work. Fake and otherwise made up security problems effectively prevent us from doing real project work and make us waste time and resources.

We will ban users immediately who submit made up fake reports to the project.

## Severity scoring

If you are familiar with [**CVSS4.0**](https://www.first.org/cvss/v4-0/specification-document), then you are welcome to provide the score of the vulnerability in your report in the shape of a vector string. There's a calculator [here](https://www.first.org/cvss/calculator/4-0). Be advised that we most likely will rescore the vulnerability however, as we know the project and its deployment scenarios and threat model best.

If you intend to _do_ provide a score yourself, please make yourself familiar with CVSS4.0 _first_ (we strongly recommend reading [the Specification](https://www.first.org/cvss/v4.0/specification-document) and [the Assessment Guide](https://www.first.org/cvss/v4-0/user-guide#Assessment-Guide)), as we will not accept reports that use it incorrectly.

Do **not** score with anything other than CVSS4.0. Scores done in any prior CVSS versions won't be accepted.

**When scoring Attack Vector, use `Adjacent` as a maximum.** OctoPrint is supposed to be deployed in a secure private network. Deployments on the public internet or other hostile networks are considered a severe misconfiguration, not the default deployment scenario. We also stress this point in several places in the FAQ and in OctoPrint itself.

## Structure and content of your report

Please make sure your report includes the following information:

- For the initial report and follow-up communications, **avoid overly long, verbose, or excessive structure** (such as headers or tables). Reports should be a few sentences describing the vulnerability. Ideally include a proof-of-concept that reproduces the issue.
- Be advised that **you as a reporter must verify the factual validity** (such as whether APIs actually exist and behave as claimed) of the content in your report prior to submission. "The AI said" is not enough, do your own due diligence!
- **If you use any kind of AI-based tool over the course of preparing your report**, be it a vulnerability scanner, a coding agent, or just an LLM to help you with translation, you **must** disclose this fact in your report! Include what specific tools you used, and in which parts of your report. **Do not** let your whole report get generated by a genAI tool, use your own words!
- Ideally, include a minimal patch with the mitigation for the report, or at least suggest a fix.
- Always include the **versions of OctoPrint** that were tested, and indicate which were found to be vulnerable.
- **Submit reports _only_ via [GHSA](https://github.com/OctoPrint/OctoPrint/security/advisories)** or via email to [security@octoprint.org](mailto:security@octoprint.org) (we strongly prefer GHSA). Submit your report as plain-text only (that includes markdown), including attachments only as needed. No PDFs, binaries, or other files that cannot be safely reviewed. If your proof-of-concept depends on a specially constructed binary file, please include a script to construct it rather than the file itself.

Reports that do not contain a potential security vulnerability (such as spam or requesting compliance or due-diligence work) will be discarded without a reply. Repeat abuse will lead to a ban.

## Public disclosure & CVE assignment

We will publish GitHub Security Advisories, and through those will also request CVEs, for valid vulnerabilities that meet the following criteria:

- The vulnerability is in OctoPrint itself, not a third party library
- The vulnerability is not already known to us
- The vulnerability is not already known to the public
- The vulnerability isn't a non-qualifying vulnerability as per the above definition

## Bounties

As a crowd-funded community project, OctoPrint is not able to offer bounties for security vulnerabilities. However, we will of course give credit to the reporter of a vulnerability in our release notes and the release announcements on the blog.

---

<center><em>This document was last updated on 2026-06-24.</em></center>
