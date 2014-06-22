var bibtex = (function(){
    "use strict";
    var exported = {};

    function StateObj(data) {
        var that = this;

        that.s = data;
        that.pos = 0;
        that.end = that.s.length;

        that.c = function() {
            return that.s[that.pos];
        };

        that.finished = function() {
            return that.pos >= that.end;
        };

        that.unfinished = function() {
            return that.pos < that.end;
        };

        return that;
    }

    function skipSpaces(state) {
        var skipped = false;

        while (state.unfinished() && (/\s/).test(state.c())) {
            ++state.pos;
            skipped = true;
        }

        return skipped;
    }

    function expect(state, c) {
        if (state.finished() || (state.c() !== c)) {
            throw "Expected " + c;
        }
        ++state.pos;
    }

    function parseWord(state) {
        var word = "";

        while (state.unfinished()) {
            if ((/\w|-/).test(state.c())) {
                word += state.c();
                ++state.pos;
            } else {
                break;
            }
        }

        return word;
    }

    function consumeBraces(state) {
        var result = "";

        while (state.unfinished() && (state.c() !== "}")) {
            var c = state.c();
            ++state.pos;

            if (c === "{") {
                c = consumeBraces(state);
            }

            result += c;
        }

        if (state.unfinished()) {
            ++state.pos;
        } else {
            throw "Missing closing braces!";
        }

        return result;
    }

    function parseValue(state) {
        var value = "";

        while (state.unfinished() && (state.c() !== ",") && (state.c() !== "}")) {
            var c = state.c();
            ++state.pos;

            if (c === "{") {
                c = consumeBraces(state);
            }

            value += c;
        }

        return value;
    }

    function parseEntry(state) {
        var entry = {},
            first = true;

        entry.type = parseWord(state);
        expect(state, "{");

        while (state.unfinished() && (state.c() !== "}")) {
            var key = parseWord(state);

            if (first) {
                entry.id = key;
                first = false;
            } else {
                skipSpaces(state);
                expect(state, "=");
                skipSpaces(state);
                entry[key] = parseValue(state);
            }

            if (state.pos < state.end) {
                if (state.c() === ",") {
                    ++state.pos;
                    skipSpaces(state);
                }
            } else {
                throw "Incomplete entry!";
            }
        }

        if (state.unfinished()) {
            ++state.pos;
        } else {
            throw "Incomplete entry!";
        }

        return entry;
    }

    exported.parse = function(s) {
        var state = new StateObj(s),
            result = [];

        while (state.unfinished()) {
            if(skipSpaces(state)) {
                continue;
            }

            if (state.c() === "@") {
                ++state.pos;
                result.push(parseEntry(state));
            } else {
                throw "Malformed input!";
            }
        }

        return result;
    };

    return exported;
})();

