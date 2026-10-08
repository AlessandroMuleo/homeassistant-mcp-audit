# homeassistant-mcp-audit

I looked at one tool in [robbrad/homeassistant-mcp](https://github.com/robbrad/homeassistant-mcp): `template_render`. It is marked `readOnlyHint: true`. This repo records what I checked and what I found.

Status: written up. I contacted the maintainer in August 2026 and published this afterwards.

## Why this tool

MCP clients use tool annotations to decide how much to ask the user. Some clients let a tool marked `readOnlyHint: true` run without a confirmation prompt. The server writes that annotation, and the client has no way to check it.

`template_render` takes a Jinja2 template from the caller and renders it with Home Assistant. I wanted to know whether "read-only" is a good enough reason to skip the prompt for this tool.

## What I checked

First, where the call goes. In `src/homeassistant_mcp/tools/specialized/template.py` the tool passes the template string to `client.render_template`, which sends a POST to Home Assistant's `/api/template` endpoint. The MCP server does not filter or limit the template. Whatever Home Assistant lets a template do, the tool lets the caller do.

Second, a CVE I suspected. CVE-2025-27516 is a sandbox bypass in Jinja2 before 3.1.6: the `|attr` filter can reach `str.format` and skip the sandbox checks. Home Assistant pins `Jinja2==3.1.6`, which has the fix. I wrote a harmless version of the test from the fix commit and ran it on both versions. It gets through on 3.1.5 and is blocked on 3.1.6. So `template_render` is not affected by this CVE on the version Home Assistant ships. I first assumed it was, and the test showed I was wrong.

## The finding

`readOnlyHint` says that a tool does not change state. It says nothing about what the tool can read. A template can read the state and attributes of every entity, and device and area data, and `template_render` has no limit on which ones. A client that trusts the annotation can run the tool on a prompt-injected request with no confirmation, and the output goes back into the model's context.

The server code does what it claims. The gap is in the annotation vocabulary: there is a hint for "does not write" but none for "may return sensitive data". There are open proposals for a `sensitiveHint` in the MCP spec.

## What I did not do

- I did not find a new CVE.
- I did not test MCP clients. How they treat `readOnlyHint` differs, and I have only checked the server side.
- I did not scan other servers. This is one tool.

## Reproducing

The CVE check needs only Python:

```
python3 -m venv v315 && v315/bin/pip install jinja2==3.1.5
python3 -m venv v316 && v316/bin/pip install jinja2==3.1.6
v315/bin/python poc/check_cve_2025_27516.py
v316/bin/python poc/check_cve_2025_27516.py
```

The script reads one harmless attribute (`__class__.__name__`) through `|attr("format")`. On 3.1.5 it prints `VULNERABLE`, on 3.1.6 it prints `blocked`.

The `readOnlyHint` part can be read in the source: the annotation is on line 20 of `template.py`, and the call to `/api/template` is in `HomeAssistantClient.render_template` in `hass/client.py`. I checked it against v3.2.1.

## Related work

- Jinja2 fix for CVE-2025-27516: [pallets/jinja@90457bb](https://github.com/pallets/jinja/commit/90457bbf33b8662926ae65cdde4c4c32e756e403) and [advisory GHSA-cpwx-vrp4-4pq7](https://github.com/pallets/jinja/security/advisories/GHSA-cpwx-vrp4-4pq7)
- Large-scale checks of annotations against tool behavior, for example DCIChecker (arXiv:2606.04769). This repo is one case in detail.
- Open MCP proposals for a `sensitiveHint` annotation, in the MCP specification repository.

## Disclosure

August 2026: I opened [issue #1](https://github.com/robbrad/homeassistant-mcp/issues/1) in the maintainer's repo, with no technical details, to ask for a private channel. As of 8 October 2026 the issue has no reply from the maintainer.

Nothing in this repo is exploit code, and the finding does not depend on a specific bug in the server.

## License

MIT, see [LICENSE](LICENSE).
