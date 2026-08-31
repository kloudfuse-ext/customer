package validate

import (
	"strings"
	"testing"
)

// Regression guard for the rule-ordering finding from the live run on
// <TEST-CLUSTER>. The shipped order (`rules`) is key-anchored-first; reversing it
// so the broad card rule runs first fragments a track2 value and leaves the
// discretionary data exposed.

func maskWith(rs []rule, line string) string {
	for _, r := range rs {
		line = r.re.ReplaceAllString(line, r.replace)
	}
	return line
}

// cardFirst is the previously-documented order that the live run showed to be buggy.
var cardFirst = []rule{rules[2], rules[0], rules[1], rules[3]}

func TestShippedOrder_track2IsClean(t *testing.T) {
	in := `{"track2": ";4111111111111111=25121011000000000000?"}`
	got := maskWith(rules, in)
	t.Logf("shipped order -> %s", got)
	if got != `{"track2": "[CSC REDACTED]"}` {
		t.Errorf("expected clean track2 masking, got: %s", got)
	}
}

func TestCardFirstOrder_regresses(t *testing.T) {
	// Documents why the order was changed: card-first leaves track data exposed.
	in := `{"track2": ";4111111111111111=25121011000000000000?"}`
	got := maskWith(cardFirst, in)
	t.Logf("card-first    -> %s", got)
	if !strings.Contains(got, "25121011000000000000") {
		t.Errorf("expected card-first order to leak track data (documents the bug), got: %s", got)
	}
}
