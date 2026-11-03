import pytest

from app.asx import core_name, find_mention, get_company, mentions, resolve, search
from app.models import HoldingIn, ResolvedHolding


def holding(ticker):
    return resolve([HoldingIn(ticker=ticker, weight=100)], [1.0])[0]


class TestDirectory:
    def test_known_company_lookup(self):
        c = get_company("CBA")
        assert c is not None
        assert c.name == "Commonwealth Bank of Australia"
        assert "CommBank" in c.aliases

    def test_unknown_company_is_none(self):
        assert get_company("ZZZZ") is None

    def test_search_prefers_ticker_prefix_then_name(self):
        assert search("bhp")[0].ticker == "BHP"
        assert "BHP" in [r.ticker for r in search("bh")]
        assert any(r.ticker == "CBA" for r in search("commonwealth"))

    def test_search_empty_query_returns_nothing(self):
        assert search("  ") == []

    def test_core_name_strips_legal_suffixes(self):
        assert core_name("BHP Group Limited") == "BHP"
        assert core_name("Woolworths Group Limited") == "Woolworths"
        assert core_name("Commonwealth Bank of Australia") == "Commonwealth Bank of Australia"


class TestResolve:
    def test_resolve_attaches_name_and_match_terms(self):
        h = holding("WOW")
        assert h.name == "Woolworths Group Limited"
        assert "Woolies" in h.aliases
        assert "Woolworths" in h.aliases

    def test_unknown_ticker_still_resolves(self):
        h = holding("ZZZZ")
        assert h.name is None and h.aliases == []


class TestMentions:
    def test_bare_ticker(self):
        assert mentions("Shares in BHP fell 3% on Monday.", holding("BHP"))

    def test_ticker_inside_other_word_does_not_match(self):
        assert not mentions("The BHPX index rose.", holding("BHP"))

    def test_lowercase_ticker_does_not_match(self):
        assert not mentions("The wow factor was missing.", holding("WOW"))

    def test_company_name_and_alias(self):
        assert mentions("CommBank lifted its dividend.", holding("CBA"))
        assert mentions("Woolworths reported weaker sales.", holding("WOW"))

    def test_headline_in_all_caps(self):
        assert mentions("WOOLWORTHS PROFIT SLUMPS", holding("WOW"))

    def test_short_names_the_press_uses(self):
        assert mentions("James Hardie lifted guidance.", holding("JHX"))
        assert mentions("a2 Milk shares jumped.", holding("A2M"))
        assert mentions("A2 Milk shares jumped.", holding("A2M"))

    def test_name_matches_either_apostrophe(self):
        # The ASX list writes "Domino's"; news sites often use a curly apostrophe.
        dmp = holding("DMP")
        assert mentions("Domino’s Pizza Enterprises cut its forecast.", dmp)
        assert mentions("Domino's Pizza Enterprises cut its forecast.", dmp)

    def test_alias_that_is_an_english_word_needs_capitals(self):
        assert mentions("Origin said gas output rose.", holding("ORG"))
        assert not mentions("The origin of the rally is unclear.", holding("ORG"))

    def test_ambiguous_ticker_needs_exchange_prefix(self):
        car = holding("CAR")
        assert not mentions("Every CAR sold in Australia needs a VIN.", car)
        assert mentions("Shares of CAR Group (ASX: CAR) jumped.", car)
        assert mentions("CAR.AX rose 2%.", car)

    @pytest.mark.parametrize(
        "ticker,sentence",
        [
            ("AFL", "The AFL grand final drew a record crowd."),
            ("NRL", "NRL ratings rose this season."),
            ("ACT", "The ACT government announced a new budget."),
            ("SPP", "The miner will raise $20 million through an SPP."),
            ("CPU", "Nvidia said CPU demand was softening."),
            ("SEC", "The SEC fined the broker."),
            ("GPT", "OpenAI's GPT-5 chatbot helped a software startup double profits."),
        ],
    )
    def test_news_acronyms_need_exchange_prefix(self, ticker, sentence):
        assert not mentions(sentence, holding(ticker))
        assert mentions(f"Shares in (ASX: {ticker}) rose.", holding(ticker))

    def test_gpt_group_by_name_still_counts(self):
        assert mentions("GPT Group lifted its distribution guidance.", holding("GPT"))

    @pytest.mark.parametrize(
        "ticker,sentence",
        [
            ("ORG", "Queensland won the State of Origin decider."),
            ("MQG", "Floods hit Port Macquarie overnight."),
            ("RIO", "Protests spread across Rio de Janeiro."),
            ("RIO", "RIO DE JANEIRO BRACES FOR STORM"),
            ("STO", "Santos FC beat Corinthians on Sunday."),
        ],
    )
    def test_places_and_events_named_like_a_company(self, ticker, sentence):
        assert not mentions(sentence, holding(ticker))

    def test_real_mention_next_to_a_lookalike_still_counts(self):
        assert mentions("Origin Energy sponsors State of Origin.", holding("ORG"))

    def test_find_mention_returns_where_it_starts(self):
        text = "State of Origin is on tonight, and Origin Energy is a sponsor."
        assert find_mention(text, holding("ORG")) == text.index("Origin Energy")
        assert find_mention("Nothing here.", holding("ORG")) is None

    def test_unknown_ticker_matches_only_by_ticker(self):
        h = ResolvedHolding(ticker="ZZZZ", weight=1.0)
        assert mentions("ZZZZ announced a capital raise.", h)
        assert not mentions("Nothing to see here.", h)
