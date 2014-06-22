# hyperion - random
Here you find a collection of random things that are useful when working with LaTeX.

## bibtex.js
A simple standalone JavaScript bibtex parser. It can be used to include your citations in a website or presentation. It only parses all entries to key-value-maps. No further processing is made (e.g. splitting of the `author` tag or parsing of the `timestamp` or `crossref`). Usage is very simple:

```javascript
var input = "<YOU BIBTEX FILE-CONTENT HERE>";
var parsed = bibtex.parse(input);
for (var i = 0; i < parsed.length; ++i) {
    console.log(parsed[i].title);
}
```

