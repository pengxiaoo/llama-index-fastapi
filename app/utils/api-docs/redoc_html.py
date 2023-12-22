"""
Script to export the ReDoc documentation page into a standalone HTML file.
Created by https://github.com/pawamoy on https://github.com/Redocly/redoc/issues/726#issuecomment-645414239
"""
import yaml
import json
import sys

"""
Usage:
    python redoc-html.py < /path/to/api.yaml > doc.html
"""

TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>Api Definitions for Traveler's App</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
    <style>
        body {
            margin: 0;
            padding: 0;
        }
    </style>
    <style data-styled="" data-styled-version="4.4.1"></style>
</head>
<body>
    <div id="redoc-container"></div>
    <script src="https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js"> </script>
    <script>
        var spec = %s;
        Redoc.init(spec, {}, document.getElementById("redoc-container"));
    </script>
</body>
</html>
"""

spec = yaml.load(sys.stdin, Loader=yaml.FullLoader)
sys.stdout.write(TEMPLATE % json.dumps(spec))
