// Faithful offline validation of the sensitive-data masking rules documented in
// kf-docs (reference/datadog/log-processing.adoc and reference/otel/logs-processing.adoc).
//
// Both the Datadog Agent (mask_sequences) and the OTel Collector (transform
// replace_pattern) compile these patterns with Go's regexp package (RE2) and
// substitute with regexp.ReplaceAllString using $1/$2 group references. This
// harness applies the identical patterns and replacements, so a pass here means
// the rules behave the same way in either agent.
//
// Run:  go test -v ./...      (from agents/security/validate)
package validate

import (
	"encoding/json"
	"regexp"
	"strings"
	"testing"
)

// rule is one mask_sequences / replace_pattern entry: a compiled pattern and its
// replacement template (Datadog replace_placeholder == OTel replacement after
// un-escaping $$ -> $).
type rule struct {
	name    string
	re      *regexp.Regexp
	replace string
}

// The four rules, verbatim from the docs (Go-string escaping, not YAML escaping).
//
// Order matters and must match the docs and helm-values: the key-anchored rules
// (CSC, credentials) run BEFORE the broad card-number rule, so a card number
// embedded in a keyed value (e.g. track2) is masked whole rather than fragmented
// by the card rule. The live run on <TEST-CLUSTER> confirmed the reversed order
// produced "[CSC REDACTED] REDACTED]=2512..." with track discretionary data left
// exposed; this order produces a clean "[CSC REDACTED]".
var rules = []rule{
	{
		name:    "mask_card_security_codes",
		re:      regexp.MustCompile(`(?i)\b(cvv2?|cvc2?|cid|pin_?block|track[12]|service_code)(["']?\s*[:=]\s*["']?)[;%]?[^\s,;"'&}]+`),
		replace: `$1$2[CSC REDACTED]`,
	},
	{
		name:    "mask_credentials",
		re:      regexp.MustCompile(`(?i)\b(password|passwd|secret(?:_?key)?|api[_-]?key|x-api-key|auth(?:oriz(?:ation|ed))?_?token|access_?token|bearer)(["']?\s*[:=]\s*["']?)[^\s,;"'&}]+`),
		replace: `$1$2[SECRET REDACTED]`,
	},
	{
		name:    "mask_card_numbers",
		re:      regexp.MustCompile(`\b(?:4\d{3}|5[1-5]\d{2}|2(?:22[1-9]|2[3-9]\d|[3-6]\d\d|7[01]\d|720)|3[47]\d{2}|30[0-5]\d|3(?:09|[689]\d)\d|6(?:011|5\d\d|4[4-9]\d|22\d)|35(?:2[89]|[3-8]\d)|62\d\d)(?:[ -]?\d){9,15}\b`),
		replace: `[CARD REDACTED]`,
	},
	{
		name:    "mask_emails",
		re:      regexp.MustCompile(`\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b`),
		replace: `***@***.***`,
	},
}

// mask applies all rules in order, exactly as the agents apply their rule list.
func mask(line string) string {
	for _, r := range rules {
		line = r.re.ReplaceAllString(line, r.replace)
	}
	return line
}

// --- redaction assertions -------------------------------------------------

func TestSensitiveValuesAreMasked(t *testing.T) {
	cases := []struct {
		desc      string
		in        string
		wantGone  []string // substrings that must NOT survive
		wantMarks []string // placeholders that MUST appear
	}{
		{
			desc:      "Visa 16 contiguous",
			in:        `pan=4111111111111111 charged`,
			wantGone:  []string{"4111111111111111"},
			wantMarks: []string{"[CARD REDACTED]"},
		},
		{
			desc:      "Mastercard 4-4-4-4 spaced",
			in:        `card 5555 5555 5555 4444 ok`,
			wantGone:  []string{"5555 5555 5555 4444", "5555555555554444"},
			wantMarks: []string{"[CARD REDACTED]"},
		},
		{
			desc:      "Amex 15-digit 4-6-5",
			in:        `amex 3782 822463 10005 auth`,
			wantGone:  []string{"3782 822463 10005"},
			wantMarks: []string{"[CARD REDACTED]"},
		},
		{
			desc:      "Discover 6011 dashed",
			in:        `num 6011-0009-9013-9424 done`,
			wantGone:  []string{"6011-0009-9013-9424"},
			wantMarks: []string{"[CARD REDACTED]"},
		},
		{
			desc:      "CVV value masked, key kept",
			in:        `cvv=123`,
			wantGone:  []string{"123"},
			wantMarks: []string{"cvv=[CSC REDACTED]"},
		},
		{
			desc:      "Track 2 fully masked (PAN + discretionary data)",
			in:        `track2=;4111111111111111=25121011000000000000?`,
			wantGone:  []string{"4111111111111111", "25121011000000000000", "REDACTED]="},
			wantMarks: []string{"track2=[CSC REDACTED]"},
		},
		{
			desc:      "password value masked, key kept",
			in:        `password=hunter2secret`,
			wantGone:  []string{"hunter2secret"},
			wantMarks: []string{"password=[SECRET REDACTED]"},
		},
		{
			desc:      "bearer token masked",
			in:        `authorization: bearer=eyJhbGciOiJIUzI1NiJ9`,
			wantGone:  []string{"eyJhbGciOiJIUzI1NiJ9"},
			wantMarks: []string{"[SECRET REDACTED]"},
		},
		{
			desc:      "email masked",
			in:        `user jane.doe+test@example.com logged in`,
			wantGone:  []string{"jane.doe+test@example.com"},
			wantMarks: []string{"***@***.***"},
		},
	}

	for _, c := range cases {
		t.Run(c.desc, func(t *testing.T) {
			got := mask(c.in)
			for _, g := range c.wantGone {
				if strings.Contains(got, g) {
					t.Errorf("sensitive value survived: %q\n  in:  %s\n  out: %s", g, c.in, got)
				}
			}
			for _, m := range c.wantMarks {
				if !strings.Contains(got, m) {
					t.Errorf("expected placeholder %q missing\n  in:  %s\n  out: %s", m, c.in, got)
				}
			}
		})
	}
}

// --- false-positive assertions -------------------------------------------

func TestNonSensitiveTextIsPreserved(t *testing.T) {
	cases := []struct {
		desc string
		in   string
	}{
		{"prose mentioning password", `the password was reset by an administrator`},
		{"prose mentioning cvv", `enter your cvv from the back of the card`},
		{"short numbers", `retrying request 12 of 34 after 5001 ms`},
		{"phone-length digits", `call 415 555 0132 for support`},
	}
	for _, c := range cases {
		t.Run(c.desc, func(t *testing.T) {
			got := mask(c.in)
			if got != c.in {
				t.Errorf("non-sensitive text was altered\n  in:  %s\n  out: %s", c.in, got)
			}
		})
	}
}

// --- JSON validity assertion (the reason $1$2 echoes key+separator) --------

func TestMaskedJSONStaysValid(t *testing.T) {
	in := `{"level":"info","msg":"charge","pan":"4111111111111111","cvv":"321","password":"s3cr3t-value","email":"a.b@corp.io","order_id":"ORD-77"}`
	got := mask(in)

	var obj map[string]any
	if err := json.Unmarshal([]byte(got), &obj); err != nil {
		t.Fatalf("masked line is not valid JSON: %v\n  out: %s", err, got)
	}
	for _, raw := range []string{"4111111111111111", "321", "s3cr3t-value", "a.b@corp.io"} {
		if strings.Contains(got, raw) {
			t.Errorf("raw value %q survived in JSON\n  out: %s", raw, got)
		}
	}
	if obj["order_id"] != "ORD-77" {
		t.Errorf("non-sensitive field order_id was altered: %v", obj["order_id"])
	}
}

// --- documented over-match (card-shaped identifiers) ----------------------

func TestDocumentedOverMatch(t *testing.T) {
	// The docs state the card rule intentionally masks other long identifiers
	// beginning with a valid card prefix. This locks that documented behavior in
	// so a future pattern change that silently stops over-matching is noticed.
	in := `order_number=4000000000000123 shipped`
	got := mask(in)
	if !strings.Contains(got, "[CARD REDACTED]") {
		t.Errorf("expected documented over-match to mask card-prefixed identifier\n  out: %s", got)
	}
}
