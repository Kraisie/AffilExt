import itertools
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Collection, Any

import adjustText
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as st
from matplotlib.gridspec import GridSpec
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset

import util
from definition.data.ArxivMetadata import ArxivMetadata
from definition.data.ExtAuthorData import ExtAuthorInfo, ExtResults
from definition.data.ExtCmdData import ExtCmdData
from definition.data.MatchedAuthorData import MatchedPaperData, MatchedAuthorInfo
from definition.data.RorDataset import ResearchOrganization
from definition.single_cmd_scheme import cmd_util
from scripts import arxiv_affiliations

_TOP_SIZE = 10
_FUNNEL_SIZE_PER_LEVEL = 2
_FUNNEL_SIZE_PER_TRANSITION = 1
_COLORS = ["#56b4e9", "#e69f00", "#009e73", "#cc79a7", "#f0e442"]  # soft blue, orange, dark cyan-lime, pink, yellow
_COLOR_TINTS = ["#79c3ee", "#faad00", "#00c590", "#d795ba", "#f3e966"]  # slightly brighter versions of _COLORS
_NAME_CUTOFF_SCORE = 70.0
_AFF_CUTOFF_SCORE = 50.0

_logger = logging.getLogger(__name__)


def _inc_dict_counter_single(stats: dict, value_key: str, by_value=1) -> None:
    if value_key in stats:
        stats[value_key] += by_value
    else:
        stats[value_key] = by_value


def _inc_dict_counter_iter(stats: dict, value_keys: Collection[str], by_value=1) -> None:
    for value_key in value_keys:
        _inc_dict_counter_single(stats, value_key, by_value)


@dataclass
class MatchStats:
    author_match_scores: list = field(default_factory=list)
    aff_match_scores: list = field(default_factory=list)


@dataclass
class ExtStats:
    extracted_authors: int = 0
    best_scores: list = field(default_factory=list)
    scores: list = field(default_factory=list)
    ext_types: dict = field(default_factory=dict)
    best_schemes: dict = field(default_factory=dict)
    schemes: dict = field(default_factory=dict)
    scores_by_scheme: dict = field(default_factory=dict)

    def inc_ext_types(self, ext_type: str) -> None:
        _inc_dict_counter_single(self.ext_types, ext_type)

    def inc_best_schemes(self, best_scheme: str) -> None:
        _inc_dict_counter_single(self.best_schemes, best_scheme)

    def inc_schemes(self, scheme: str) -> None:
        _inc_dict_counter_single(self.schemes, scheme)

    def add_score_to_scheme(self, scheme: str, score: float) -> None:
        if scheme in self.scores_by_scheme:
            self.scores_by_scheme[scheme].append(score)
        else:
            self.scores_by_scheme[scheme] = [score]


@dataclass
class CmdStats:
    extracted_cmds: int = 0
    most_used_doc_classes: dict = field(default_factory=dict)
    most_used_cmd_names: dict = field(default_factory=dict)
    most_used_cmd_combinations: dict = field(default_factory=dict)

    def inc_doc_classes(self, doc_classes: list[str]) -> None:
        _inc_dict_counter_iter(self.most_used_doc_classes, doc_classes)

    def inc_cmd_names(self, cmd_names: list[str]) -> None:
        _inc_dict_counter_iter(self.most_used_cmd_names, cmd_names)

    def inc_cmd_combinations(self, cmd_combinations: str) -> None:
        _inc_dict_counter_single(self.most_used_cmd_combinations, cmd_combinations)


@dataclass
class FileStats:
    total_papers: int = 0
    no_latex: int = 0
    no_cmds: int = 0
    no_ext: int = 0
    no_matched: int = 0

    def get_funnel_numbers(self):
        return [
            self.total_papers,
            self.total_papers - self.no_latex,
            self.total_papers - self.no_latex - self.no_cmds,
            self.total_papers - self.no_latex - self.no_cmds - self.no_ext,
            self.total_papers - self.no_latex - self.no_cmds - self.no_ext - self.no_matched,
        ]


@dataclass
class Stats:
    file_stats: FileStats = field(default_factory=FileStats)
    cmd_stats: CmdStats = field(default_factory=CmdStats)
    ext_stats: ExtStats = field(default_factory=ExtStats)
    match_stats: MatchStats = field(default_factory=MatchStats)


@dataclass
class CombinedData:
    arxiv: ArxivMetadata
    ext_cmds: ExtCmdData
    ext_authors: ExtAuthorInfo
    matched: MatchedPaperData


def _generate_fg_dataset_country(filtered_papers: list[MatchedPaperData]) -> None:
    temp_nodes = {}
    temp_links = {}
    for paper in filtered_papers:
        paper_countries = set()
        for author in paper.matched_authors:
            for affiliation in author.affiliations:
                for loc in affiliation.matched_ror.locations:
                    paper_countries.add(loc.country_name)

        if len(paper_countries) <= 1:
            continue

        # sort the countries so the combinations are the same order if the same 2 countries appear in different order
        sorted_affs = sorted(paper_countries)
        for c1, c2 in itertools.combinations(sorted_affs, 2):
            if c1 in temp_nodes:
                temp_nodes[c1] += 1
            else:
                temp_nodes[c1] = 1

            if c2 in temp_nodes:
                temp_nodes[c2] += 1
            else:
                temp_nodes[c2] = 1

            key = (c1, c2)
            if key in temp_links:
                temp_links[key] += 1
            else:
                temp_links[key] = 1

    nodes = []
    for country, occ in temp_nodes.items():
        nodes.append({
            "id": country,
            "name": country,
            "occ": occ
        })

    links = []
    for key, value in temp_links.items():
        node1_id, node2_id = key
        links.append({
            "source": node1_id,
            "target": node2_id,
            "strength": value
        })

    dataset = {
        "nodes": nodes,
        "links": links
    }

    # do not include "py/object" fields in json as this will not be read by jsonpickle
    util.write_obj_to_json(util.get_stats_dir(), util.FORCE_GRAPH_DATASET_COUNTRY, dataset, unpicklable=False)


# could just include the files instead of creating them via src, but meh
def _save_fgw_html():
    html = f"""<!-- based on the examples from https://github.com/vasturiano/force-graph -->
<head>
    <style> body {{
        margin: 0;
    }} </style>
    <script src="//unpkg.com/force-graph"></script>
    <script src="//unpkg.com/d3"></script>
    <!--  <script src="../../dist/force-graph.js"></script>-->
</head>
<body>
<div id="graph"></div>
<script>
    const prefersDarkScheme = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (prefersDarkScheme) {{
        bgColor = "#101020"
        edgeColor = "rgba(200, 200, 200, 0.1)"
    }} else {{
        bgColor = "#DCDCE6"
        edgeColor = "rgba(20, 20, 20, 0.1)"
    }}

    fetch('{util.FORCE_GRAPH_DATASET_COUNTRY}').then(res => res.json()).then(data => {{
        const elem = document.getElementById('graph');
        const Graph = new ForceGraph(elem)
            .graphData(data)
            .backgroundColor(bgColor)
            .nodeId("id")
            .nodeVal(node => node.occ / 1000)  // use value (occurrences of organization in dataset) as node size
            .nodeLabel(node => node.name)
            .linkColor(() => edgeColor)
            .linkSource("source")
            .linkTarget("target")
            .d3Force("link").distance(link => link.strength / 4);  // the higher the strength, the closer bot nodes
    }});
</script>
</body>"""
    util.write_to_file(util.get_stats_dir(), util.FORCE_GRAPH_DATASET_COUNTRY.replace("json", "html"), html)


def _save_fgi_html():
    html = f"""<!-- based on the examples from https://github.com/vasturiano/force-graph -->
<head>
    <style> body {{
        margin: 0;
    }} </style>
    <script src="//unpkg.com/force-graph"></script>
    <script src="//unpkg.com/d3"></script>
    <!--  <script src="../../dist/force-graph.js"></script>-->
</head>
<body>
<div id="graph"></div>
<script>
    const prefersDarkScheme = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (prefersDarkScheme) {{
        bgColor = "#101020"
        edgeColor = "rgba(200, 200, 200, 0.1)"
    }} else {{
        bgColor = "#DCDCE6"
        edgeColor = "rgba(20, 20, 20, 0.1)"
    }}

    fetch('{util.FORCE_GRAPH_DATASET_INST}').then(res => res.json()).then(data => {{
        const elem = document.getElementById('graph');
        const Graph = new ForceGraph(elem)
            .graphData(data)
            .backgroundColor(bgColor)
            .nodeId("id")
            .nodeVal(node => node.occ / 100)  // use value (occurrences of organization in dataset) as node size
            .nodeLabel(node => `${{node.name}} (${{node.country}})`)
            .nodeAutoColorBy("country")  // color nodes based on group (ROR country)
            .onNodeClick(node => window.open(`https://ror.org/${{node.id}}`))
            .linkColor(() => edgeColor)
            .linkSource("source")
            .linkTarget("target")
            .d3Force("link").distance(link => link.strength);  // the higher the strength, the closer both nodes
    }});
</script>
</body>"""
    util.write_to_file(util.get_stats_dir(), util.FORCE_GRAPH_DATASET_INST.replace("json", "html"), html)


def _create_dataset(nodes: dict, links: dict) -> dict:
    ds_nodes = []
    for ror_id, ror_data in nodes.items():
        ds_nodes.append({
            "id": ror_id,
            "name": ror_data["name"],
            "country": ror_data["country"],
            "occ": ror_data["occ"],
        })

    ds_links = []
    for key, value in links.items():
        node1_id, node2_id = key
        ds_links.append({
            "source": node1_id,
            "target": node2_id,
            "strength": value
        })

    return {
        "nodes": ds_nodes,
        "links": ds_links
    }


def _add_link(links: dict, node1: ResearchOrganization, node2: ResearchOrganization) -> None:
    key = (node1.get_ror_id(), node2.get_ror_id())
    if key in links:
        links[key] += 1
    else:
        links[key] = 1


def _add_node(nodes: dict, node: ResearchOrganization) -> None:
    node_id = node.get_ror_id()
    if node_id in nodes:
        nodes[node_id]["occ"] += 1
    else:
        nodes[node_id] = {
            "name": node.names[0],
            "country": node.locations[0].country_name,
            "occ": 1
        }


# force-graph (JS): https://github.com/vasturiano/force-graph
# dataset-format:
# {
#   "nodes": [
#       {
#           "id": "node id",                        <- ROR ID without URL-Base
#           "name": "node label",                   <- first name of ROR org
#           "country": "node country"               <- first location country of ROR org
#           "occ": 1,                             <- size of node, number of occurrences in dataset
#       }, ...
#   ],
#   "links": [
#       {
#           "source": "source node id",
#           "target": "target node id",
#           "strength": "spring force of edge"      <- occurrences of source and target in dataset
#       }
#   ],
# }
def _generate_fg_dataset_institution(filtered_papers: list[MatchedPaperData]) -> None:
    temp_nodes = {}
    temp_links = {}
    for paper in filtered_papers:
        paper_affilitions = set()
        for author in paper.matched_authors:
            for affiliation in author.affiliations:
                paper_affilitions.add(affiliation.matched_ror)

        if len(paper_affilitions) <= 1:
            continue

        # sort the orgs so the combinations are the same order if the same 2 orgs appear in different order
        sorted_affs = sorted(paper_affilitions, key=lambda x: x.get_ror_id())
        for aff1, aff2 in itertools.combinations(sorted_affs, 2):
            _add_node(temp_nodes, aff1)
            _add_node(temp_nodes, aff2)
            _add_link(temp_links, aff1, aff2)

    dataset = _create_dataset(temp_nodes, temp_links)

    # do not include "py/object" fields in json as this will not be read by jsonpickle
    util.write_obj_to_json(util.get_stats_dir(), util.FORCE_GRAPH_DATASET_INST, dataset, unpicklable=False)


def _get_paper_affiliation_set(authors: list[MatchedAuthorInfo]) -> set[ResearchOrganization]:
    ror_orgs = set()
    for author in authors:
        for affiliation in author.affiliations:
            ror_orgs.add(affiliation.matched_ror)

    return ror_orgs


def _graph_top_affiliations(filtered_papers: list[MatchedPaperData]) -> None:
    affiliations = {}
    for paper in filtered_papers:
        paper_ror_orgs = _get_paper_affiliation_set(paper.matched_authors)
        for ror_org in paper_ror_orgs:
            ror_id = ror_org.ror_id
            if ror_id not in affiliations:
                affiliations[ror_id] = {
                    "name": ror_org.names[0],
                    "occ": 1
                }
            else:
                affiliations[ror_id]["occ"] += 1

    top_affiliations = {k: v for k, v in sorted(affiliations.items(), key=lambda x: -x[1]["occ"])[:_TOP_SIZE]}
    x_values = [v["name"] for _, v in top_affiliations.items()]
    y_values = [v["occ"] for _, v in top_affiliations.items()]
    fix, ax = plt.subplots()
    ax.bar(x_values, y_values, align='center', color=_COLORS[0])
    ax.invert_xaxis()
    ax.set_ylabel("Veröffentlichungen")
    ax.set_title("Institutionen, die an den meisten Veröffentlichungen beteiligt sind")
    plt.xticks(rotation=60, ha="right")
    plt.savefig(util.get_stats_dir() / "TopPublishingInstitutions", dpi=300, bbox_inches="tight")


def _graph_top_authors(filtered_papers: list[MatchedPaperData]) -> None:
    authors = {}
    for paper in filtered_papers:
        for author in paper.matched_authors:
            arxiv_author_name = author.arxiv_name.strip()
            if arxiv_author_name in authors:
                authors[arxiv_author_name]["occ"] += 1
                authors[arxiv_author_name]["aff"] += [aff.matched_ror.ror_id for aff in author.affiliations]
            else:
                authors[arxiv_author_name] = {"occ": 1, "aff": []}

    # replace list of affiliations with number of unique affiliations
    count_aff = lambda x: {"occ": x["occ"], "aff": len(set(x["aff"]))}
    authors = {k: count_aff(v) for k, v in authors.items()}

    top_authors_by_papers = {k: v for k, v in sorted(authors.items(), key=lambda x: -x[1]["occ"])[:_TOP_SIZE]}
    top_authors_by_affiliations = {k: v for k, v in sorted(authors.items(), key=lambda x: -x[1]["aff"])[:_TOP_SIZE]}
    authors_occ_values = [v["occ"] for v in authors.values()]
    authors_aff_values = [v["aff"] for v in authors.values()]
    pearson_r = st.pearsonr(authors_occ_values, authors_aff_values)
    _logger.debug("Correlation AuthorPapers <-> AuthorAffiliations: %s", pearson_r)

    max_y_value = list(top_authors_by_affiliations.values())[0]["aff"]
    max_x_value = list(top_authors_by_papers.values())[0]["occ"]

    fig = plt.figure(figsize=(6, 6))
    grid = fig.add_gridspec(
        2, 2, width_ratios=(4, 1), height_ratios=(1, 4),
        left=0.1, right=0.9, bottom=0.1, top=0.9, wspace=0.05, hspace=0.05
    )
    ax = fig.add_subplot(grid[1, 0])
    hist_x = fig.add_subplot(grid[0, 0], sharex=ax)
    hist_y = fig.add_subplot(grid[1, 1], sharey=ax)
    hist_x.tick_params(axis="x", labelbottom=False)
    hist_y.tick_params(axis="y", labelleft=False)
    hist_x.hist(authors_occ_values, color=_COLORS[0], bins=max_x_value)
    hist_y.hist(authors_aff_values, color=_COLORS[0], bins=max_y_value, orientation='horizontal')

    # prevent stuff like "2.5" as a number of affiliations
    y_ticks = range(0, max_y_value + 2, 2)
    ax.set_yticks(y_ticks)
    ax.scatter(authors_occ_values, authors_aff_values, color=_COLORS[0], marker=".", alpha=0.5, edgecolors="none")

    # add plot for tendency
    polynomial_fit = np.poly1d(np.polyfit(authors_occ_values, authors_aff_values, 1))
    def_space = np.linspace(0, list(top_authors_by_papers.values())[0]["occ"], 100)
    y_values = polynomial_fit(def_space)
    # limit tendency plot to visible area
    y_mask = (y_values >= 0) & (y_values <= max_y_value)
    limited_def_space = def_space[y_mask]
    limited_y_values = y_values[y_mask]
    lin_reg, = ax.plot(limited_def_space, limited_y_values, linestyle="dashed", c=_COLORS[3], lw=0.75, alpha=0.75)

    # add labels for top authors
    texts = []
    for name, values in authors.items():
        if name in top_authors_by_papers or name in top_authors_by_affiliations:
            texts.append(ax.annotate(name, (values["occ"], values["aff"]), ha="center", va="center"))

    adjustText.adjust_text(
        texts, ax=ax, arrowprops={"arrowstyle": "-", "color": _COLORS[1], "lw": 0.3},
        expand=(2.0, 1.5), force_text=(1.5, 0.75),  # expand area to place text in
    )

    ax.set_xlabel("Veröffentlichungen")
    ax.set_ylabel("Anzahl von Affiliationen")
    ax.legend([lin_reg], ["Tendenz"], loc="lower right")
    fig.suptitle("Anzahl der Veröffentlichungen von Autoren in Bezug auf Anzahl von Affiliationen")
    plt.savefig(util.get_stats_dir() / "AuthorPapersAffiliations", dpi=300, bbox_inches="tight")


def _get_ror_org_occ(filtered_papers: list[MatchedPaperData]) -> dict:
    ror_orgs = {}
    for paper in filtered_papers:
        for author in paper.matched_authors:
            for affiliation in author.affiliations:
                ror_org = affiliation.matched_ror
                ror_id = ror_org.ror_id
                if ror_id not in ror_orgs:
                    ror_orgs[ror_id] = 1
                else:
                    ror_orgs[ror_id] += 1

    return ror_orgs


def _print_unique_affiliations(filtered_papers: list[MatchedPaperData]) -> None:
    unique_ror_orgs = _get_ror_org_occ(filtered_papers)
    print(f"Unique ROR affiliations: {len(unique_ror_orgs)}")


def _print_unique_authors(filtered_papers: list[MatchedPaperData]) -> None:
    arxiv_names = set()
    ext_names = set()
    for paper in filtered_papers:
        for author in paper.matched_authors:
            arxiv_names.add(author.arxiv_name.strip())
            ext_names.add(author.ext_name)

    print(f"Unique authors by ArXiv name: {len(arxiv_names)}")
    print(f"Unique authors by extracted name: {len(ext_names)}")


def _print_basic_author_stats(filtered_papers: list[MatchedPaperData]) -> None:
    _print_unique_authors(filtered_papers)
    _print_unique_affiliations(filtered_papers)


def _filter_by_cutoff(combined_data: list[CombinedData]) -> list[MatchedPaperData]:
    filtered_papers = []
    for paper in combined_data:
        matched_data = paper.matched
        if not matched_data:
            continue

        filtered_authors = []
        for author in matched_data.matched_authors:
            if author.score < _NAME_CUTOFF_SCORE:
                continue

            filtered_affs = []
            for affiliation in author.affiliations:
                if affiliation.score >= _NAME_CUTOFF_SCORE:
                    filtered_affs.append(affiliation)

            if len(filtered_affs) == 0:
                continue

            filtered_authors.append(MatchedAuthorInfo(author.arxiv_name, author.ext_name, author.score, filtered_affs))

        filtered_papers.append(MatchedPaperData(filtered_authors))

    return filtered_papers


def _get_best_extraction(ext_authors: ExtAuthorInfo) -> ExtResults:
    extractions = ext_authors.extractions
    best = extractions[0]
    for extraction in extractions[1:]:
        if extraction.score > best.score:
            best = extraction

    return best


def _graph_best_ext_scores_over_time(combined_data: list[CombinedData]) -> None:
    month_scores = {}
    for paper_data in combined_data:
        arxiv_metadata = paper_data.arxiv
        published_on = arxiv_metadata.published_on  # format: "%Y-%m-%dT%H:%M:%SZ"

        ext_authors = paper_data.ext_authors
        if not ext_authors or len(ext_authors.extractions) == 0:
            continue

        best_ext = _get_best_extraction(paper_data.ext_authors)
        year_month = published_on[0:7]  # YYYY-MM
        if year_month in month_scores:
            month_scores[year_month].append(best_ext.score)
        else:
            month_scores[year_month] = [best_ext.score]

    avg_month_scores = {k: sum(v) / len(v) for k, v in month_scores.items()}
    sorted_month_scores = _sort_dict(avg_month_scores, lambda x: int(x[0].replace("-", "")))
    x_pos = np.arange(len(sorted_month_scores))
    fig, ax = plt.subplots()
    ax.bar(x_pos, sorted_month_scores.values(), align="center", color=_COLORS[0])

    polynomial_fit = np.poly1d(
        np.polyfit(range(len(sorted_month_scores)), list(sorted_month_scores.values()), 7)
    )
    def_space = np.linspace(0, len(sorted_month_scores), 100)
    lin_reg, = ax.plot(def_space, polynomial_fit(def_space), linestyle="dashed", c=_COLORS[3], lw=0.75, alpha=0.75)

    ax.set_xlabel("Durchschnittliche Punktzahl")
    ax.set_ylabel("Veröffentlichungsmonat")
    ax.set_xticks(x_pos[::10], labels=list(sorted_month_scores.keys())[::10], rotation=60)
    ax.set_title("Durchschnittliche Punktzahl nach Erscheinungsmonat")
    plt.figlegend([lin_reg], ["Tendenz"], loc="lower right")
    plt.savefig(util.get_stats_dir() / "BestScoresOverTime", dpi=300, bbox_inches="tight")


def _graph_name_scores_and_aff_scores(stats: Stats) -> None:
    name_scores = stats.match_stats.author_match_scores
    aff_scores = stats.match_stats.aff_match_scores
    name_avg = sum(name_scores) / len(name_scores)
    aff_avg = sum(aff_scores) / len(aff_scores)

    fig, ax = plt.subplots()
    ax.hist(aff_scores, histtype="barstacked", bins=50, color=_COLORS[0], label="Punktzahlen für Affiliation-Matchings")
    ax.hist(name_scores, histtype="barstacked", bins=50, color=_COLORS[1], rwidth=0.6,
            label="Punktzahlen für Namen-Matchings")
    ax.axvline(x=aff_avg, color=_COLORS[0], ls="--", lw=0.7, alpha=0.5, label="Durchschnitt Affiliation-Matchings")
    ax.axvline(x=name_avg, color=_COLORS[1], ls="--", lw=0.7, alpha=0.5, label="Durchschnitt Namen-Matchings")
    ax.set_title("Punktzahlen der Matchings")
    ax.legend(loc="upper left")
    plt.savefig(util.get_stats_dir() / "MatchingScoresHist", dpi=300, bbox_inches="tight")


def _graph_scores_by_scheme_occ(stats: Stats):
    schemes = stats.ext_stats.schemes  # schemes with occ
    scores_by_scheme = stats.ext_stats.scores_by_scheme  # schemes with scores

    scores = []
    occ = []
    names = []
    for scheme_name, scheme_occ in schemes.items():
        scheme_scores = scores_by_scheme[scheme_name]
        avg_score = sum(scheme_scores) / len(scheme_scores)
        scores.append(avg_score)
        occ.append(scheme_occ)
        names.append(scheme_name)

    fig, ax = plt.subplots()
    ax.scatter(occ, scores, color=_COLORS[0], marker=".", alpha=0.5, edgecolors="none")
    texts = []
    for i, name in enumerate(names):
        if scores[i] > 0.75 and occ[i] > 250:
            texts.append(ax.annotate(name, (occ[i], scores[i]), ha="center", va="bottom"))

    adjustText.adjust_text(
        texts, arrowprops={"arrowstyle": "-", "color": _COLORS[1], "lw": 0.3},
        expand=(1.5, 2.5), force_text=(0.5, 1.0),  # expand area to place text in
        only_move="x+y+"  # only move the text up and right
    )

    ax.set_xlabel("Häufigkeit")
    ax.set_ylabel("Durchschnittliche Punktzahl")
    ax.set_title("Durchschnittliche Punktzahlen und Häufigkeit der Nutzung von Extraktionschemata")
    plt.savefig(util.get_stats_dir() / "ExtScoresOccByScheme", dpi=300, bbox_inches="tight")


def _sort_dict(data_dict: dict, sort_func: callable) -> dict:
    return {k: v for k, v in sorted(data_dict.items(), key=sort_func)}


def _sort_dict_by_value_desc(stats_dict: dict) -> dict:
    return _sort_dict(stats_dict, lambda x: -x[1])


def _graph_ext_scores_by_scheme(stats: Stats):
    scheme_avg_score = {}
    for scheme, scores in stats.ext_stats.scores_by_scheme.items():
        scheme_avg_score[scheme] = sum(scores) / len(scores)

    sorted_dict = _sort_dict_by_value_desc(scheme_avg_score)
    y_pos = np.arange(len(sorted_dict))
    fig, ax = plt.subplots()
    ax.barh(y_pos, sorted_dict.values(), align="center", color=_COLORS[0])
    ax.set_yticks(y_pos, labels=sorted_dict.keys())
    ax.invert_yaxis()
    ax.set_xlabel("Durchschnittliche Punktzahl")
    ax.set_title("Durchschnittliche Punktzahlen nach Extraktionschema")
    plt.savefig(util.get_stats_dir() / "ExtScoresByScheme", dpi=300, bbox_inches="tight")


def _graph_best_ext_scores(stats: Stats) -> None:
    best_scores = stats.ext_stats.best_scores
    best_avg = sum(best_scores) / len(best_scores)

    fig, ax = plt.subplots()
    ax.hist(best_scores, histtype="barstacked", bins=50, color=_COLORS[0], label="Beste Punktzahlen")
    ax.axvline(x=best_avg, color=_COLORS[1], ls="--", lw=0.7, alpha=0.5, label="Durchschnitt bester Punktzahlen")
    ax.set_title(f"Punktzahlen der besten Extraktionen (n = {len(best_scores)})")
    ax.legend(loc="upper left")
    plt.savefig(util.get_stats_dir() / "BestExtScoresHist", dpi=300, bbox_inches="tight")


def _graph_ext_scores(stats: Stats) -> None:
    best_scores = stats.ext_stats.best_scores
    all_scores = stats.ext_stats.scores
    best_avg = sum(best_scores) / len(best_scores)
    all_avg = sum(all_scores) / len(all_scores)

    fig, ax = plt.subplots()
    ax.hist(all_scores, histtype="barstacked", bins=50, color=_COLORS[0], label="Alle Punktzahlen")
    ax.hist(best_scores, histtype="barstacked", bins=50, color=_COLORS[1], rwidth=0.6, label="Beste Punktzahlen")
    ax.axvline(x=all_avg, color=_COLORS[0], ls="--", lw=0.7, alpha=0.5, label="Durchschnitt aller Punktzahlen")
    ax.axvline(x=best_avg, color=_COLORS[1], ls="--", lw=0.7, alpha=0.5, label="Durchschnitt bester Punktzahlen")
    ax.set_title("Punktzahlen der Extraktionen")
    ax.legend(loc="upper left")
    plt.savefig(util.get_stats_dir() / "ExtScoresHist", dpi=300, bbox_inches="tight")


def _graph_hbar(top_list: dict, title: str, file_name: str) -> None:
    y_pos = np.arange(len(top_list))
    fig, ax = plt.subplots()
    bars = ax.barh(y_pos, top_list.values(), align="center", color=_COLORS[0])
    ax.bar_label(bars, top_list.values())
    ax.set_yticks(y_pos, labels=top_list.keys())
    ax.invert_yaxis()
    ax.set_xlabel("Häufigkeit")
    ax.set_title(title)
    plt.savefig(util.get_stats_dir() / file_name, dpi=300, bbox_inches="tight")


def _graph_hbar_dict(stats_dict: dict, title: str, file_name: str) -> None:
    sorted_dict = _sort_dict_by_value_desc(stats_dict)
    top_list = dict(list(sorted_dict.items())[:_TOP_SIZE])
    other = dict(list(sorted_dict.items())[_TOP_SIZE:])
    other_occ = sum(other.values())
    top_list["other"] = other_occ
    _graph_hbar(top_list, title, file_name)


def _graph_most_used_cmd_combinations(stats: Stats) -> None:
    n = sum(list(stats.cmd_stats.most_used_cmd_combinations.values()))
    _graph_hbar_dict(
        stats.cmd_stats.most_used_cmd_combinations,
        f"Meistgenutzte Befehlskombinationen (n = {n})",
        "TopCmdCombinations"
    )


def _graph_most_used_cmd_names(stats: Stats) -> None:
    n = sum(list(stats.cmd_stats.most_used_cmd_names.values()))
    _graph_hbar_dict(
        stats.cmd_stats.most_used_cmd_names,
        f"Meistgenutzte Befehlsnamen (n = {n})",
        "TopCmdNames"
    )


def _graph_most_used_doc_classes(stats: Stats) -> None:
    n = sum(list(stats.cmd_stats.most_used_doc_classes.values()))
    _graph_hbar_dict(
        stats.cmd_stats.most_used_doc_classes,
        f"Meistgenutzte Documentclasses (n = {n})",
        "TopDocClasses"
    )


def _get_funnel_level_coords(funnel_numbers: list[int]) -> list[dict]:
    curr_total = funnel_numbers[0]
    curr_y = len(funnel_numbers) * _FUNNEL_SIZE_PER_LEVEL + (len(funnel_numbers) - 1) * _FUNNEL_SIZE_PER_TRANSITION
    coords = [
        {
            "y_coords": [curr_y, curr_y := curr_y - _FUNNEL_SIZE_PER_LEVEL],
            "x1_coords": [0, 0],
            "x2_coords": [curr_total, curr_total]
        }
    ]
    for funnel_number in funnel_numbers[1:]:
        transition_y = [curr_y, curr_y := curr_y - _FUNNEL_SIZE_PER_TRANSITION]
        level_y = [curr_y, curr_y := curr_y - _FUNNEL_SIZE_PER_LEVEL]

        diff_levels = curr_total - funnel_number
        curr_total -= diff_levels
        level_offset = int(diff_levels / 2)
        level_x1 = coords[-1]["x1_coords"][0] + level_offset
        level_x2 = coords[-1]["x2_coords"][0] - level_offset
        transition_x1 = [coords[-1]["x1_coords"][0], level_x1]
        transition_x2 = [coords[-1]["x2_coords"][0], level_x2]

        # transition between previous level and next level
        coords.append({
            "y_coords": transition_y,
            "x1_coords": transition_x1,
            "x2_coords": transition_x2
        })

        # next level
        coords.append({
            "y_coords": level_y,
            "x1_coords": [level_x1, level_x1],
            "x2_coords": [level_x2, level_x2]
        })

    return coords


def _graph_funnel_file_stats(stats: Stats) -> None:
    file_stats = stats.file_stats
    funnel_numbers = file_stats.get_funnel_numbers()
    funnel_level_coords = _get_funnel_level_coords(funnel_numbers)

    fig, ax = plt.subplots()
    colors = [_COLORS[0], _COLOR_TINTS[0]]
    for i, funnel_level_coord in enumerate(funnel_level_coords):
        ax.fill_betweenx(
            funnel_level_coord["y_coords"], funnel_level_coord["x1_coords"], funnel_level_coord["x2_coords"],
            color=colors[i % len(colors)]
        )

    y_ticks = [level["y_coords"][0] - (_FUNNEL_SIZE_PER_LEVEL / 2) for level in funnel_level_coords[::2]]
    y_labels = ["API-Anfrage", "LaTeX-Download", "Cmd-Extraktion", "Author-Extraktion", "ROR-Matching"]
    ax.set_xticks([])
    ax.set_yticks(y_ticks, labels=y_labels)
    text_x_pos = int(file_stats.total_papers / 2)
    for text_y_pos, funnel_number in zip(y_ticks, funnel_numbers):
        ax.text(
            text_x_pos, text_y_pos, str(funnel_number), ha="center", va="center",
            fontweight="bold", fontsize=16, color=_COLOR_TINTS[1]
        )

    # hide the axes and ticks but keep labels
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis="both", which="both", length=0)

    ax.set_ylabel("Programmabschnitt")
    ax.set_title("Valide Veröffentlichungen nach Programmabschnitten")
    plt.grid(visible=False)
    plt.savefig(util.get_stats_dir() / "ValidPapersPerStep", dpi=300, bbox_inches="tight")


def _get_cost_intersection(
        cost1: np.ndarray[Any, np.dtype[np.floating]], cost2: np.ndarray[Any, np.dtype[np.floating]],
        limit: int, step: int
) -> int:
    intersection = -1
    for i in range(min(len(cost1), len(cost2))):
        if cost1[i] < cost2[i]:
            intersection = i * (limit // step)
            break

    return intersection


def _get_laptop_llm_cost(papers: np.ndarray[Any, np.dtype[np.floating]]) -> np.ndarray[Any, np.dtype[np.floating]]:
    runtime_per_cmd_ext_ms = 6 * 1000 / 14611  # 3 seconds for cmd extraction in 14611 papers
    runtime_per_aff_ext_ms = 206 * 1000 / 14385  # 2m 3s for author data extraction in 14385 papers with ext cmds
    runtime_per_matching_ms = 927 * 1000 / 11107  # 19m 25s for ror matching in 11107 papers with ext author data

    # latex cmd ext + aff ext for successful latex cmds + matching for successful aff ext
    runtime_per_paper = (
            runtime_per_cmd_ext_ms +  # assume cmd ext always works
            ((14385 / 14611) * runtime_per_aff_ext_ms) +
            ((11107 / 14611) * runtime_per_matching_ms)
    )

    invest_cost_euro = 1142
    laptop_power_draw_w = 95  # upper limit, psu can not supply more than this
    kwh_price_germany_euro = 0.4  # https://www.swd-ag.de/pk/strom-gas-wasser/strom/strompreise/
    laptop_cost = (
            invest_cost_euro +  # base price of the laptop (euro)
            (papers * _ms_to_h(runtime_per_paper)) *  # time needed for n papers (h)
            # price of power when running (power draw (kW) * power cost (euro/kWh))
            (laptop_power_draw_w / 1000) * kwh_price_germany_euro
    )

    in_tokens_per_paper = 353.9
    out_tokens_per_paper = 106.86
    in_tokens_price_per_million_euro = 2.40  # 2.50 USD / 1m -> 2.40 EUR / 1m
    out_tokens_price_per_million_euro = 0.962  # 10 USD / 10m -> 9.62 EUR / 10m -> 0.962 EUR / 1m
    in_token_price = in_tokens_price_per_million_euro / 1_000_000
    out_token_price = out_tokens_price_per_million_euro / 1_000_000
    required_in_tokens = (14611 - 11107) / 14611 * in_tokens_per_paper
    required_out_tokens = (14611 - 11107) / 14611 * out_tokens_per_paper
    llm_cost = papers * ((required_in_tokens * in_token_price) + (required_out_tokens * out_token_price))

    return laptop_cost + llm_cost


def _get_llm_cost(papers: np.ndarray[Any, np.dtype[np.floating]]) -> np.ndarray[Any, np.dtype[np.floating]]:
    in_tokens_per_paper = 353.9
    out_tokens_per_paper = 106.86
    in_tokens_price_per_million_euro = 2.40  # 2.50 USD / 1m -> 2.40 EUR / 1m
    out_tokens_price_per_million_euro = 0.962  # 10 USD / 10m -> 9.62 EUR / 10m -> 0.962 EUR / 1m
    in_token_price = in_tokens_price_per_million_euro / 1_000_000
    out_token_price = out_tokens_price_per_million_euro / 1_000_000
    return papers * ((in_tokens_per_paper * in_token_price) + (out_tokens_per_paper * out_token_price))


def _get_server_cost(papers: np.ndarray[Any, np.dtype[np.floating]]) -> np.ndarray[Any, np.dtype[np.floating]]:
    monthly_cost_euro = 95.99  # yes, using float for currencies :P
    hourly_cost_euro = monthly_cost_euro / 720  # server is billed hourly
    runtime_per_paper = _get_laptop_runtime_per_paper()  # same as laptop to make it equivalent

    # every started hour gets billed
    # https://docs.hetzner.com/general/others/new-billing-model/#how-precisely-does-hetzner-calculate-the-hourly-billing
    return np.ceil(papers * _ms_to_h(runtime_per_paper)) * hourly_cost_euro


def _ms_to_h(ms: float) -> float:
    return ms / 3_600_000.0


def _get_laptop_runtime_per_paper() -> float:
    runtime_per_cmd_ext_ms = 6 * 1000 / 14611  # 3 seconds for cmd extraction in 14611 papers
    runtime_per_aff_ext_ms = 206 * 1000 / 14385  # 2m 3s for author data extraction in 14385 papers with ext cmds
    runtime_per_matching_ms = 927 * 1000 / 11107  # 19m 25s for ror matching in 11107 papers with ext author data
    # assuming every paper is viable for all steps
    return runtime_per_cmd_ext_ms + runtime_per_aff_ext_ms + runtime_per_matching_ms


def _get_laptop_cost(papers: np.ndarray[Any, np.dtype[np.floating]]) -> np.ndarray[Any, np.dtype[np.floating]]:
    invest_cost_euro = 1142
    runtime_per_paper = _get_laptop_runtime_per_paper()
    laptop_power_draw_w = 95  # upper limit, psu can not supply more than this
    kwh_price_germany_euro = 0.4  # https://www.swd-ag.de/pk/strom-gas-wasser/strom/strompreise/
    return (
            invest_cost_euro +  # base price of the laptop (euro)
            (papers * _ms_to_h(runtime_per_paper)) *  # time needed for n papers (h)
            # price of power when running (power draw (kW) * power cost (euro/kWh))
            (laptop_power_draw_w / 1000) * kwh_price_germany_euro
    )


def _graph_ext_cost() -> None:
    limit = 5_000_000
    step = 500
    x_pos = np.linspace(0, limit, step)
    laptop_cost = _get_laptop_cost(x_pos)
    server_cost = _get_server_cost(x_pos)
    llm_cost = _get_llm_cost(x_pos)
    laptop_llm_cost = _get_laptop_llm_cost(x_pos)

    print(f"Laptop cost after {limit} papers: {laptop_cost[-1]:.2f} Euro")
    print(f"Server cost after {limit} papers: {server_cost[-1]:.2f} Euro")
    print(f"GPT-4o cost after {limit} papers: {llm_cost[-1]:.2f} Euro")
    print(f"Laptop + GPT-4o (for failed exts) cost after {limit} papers: {laptop_llm_cost[-1]:.2f} Euro")

    print(f"Laptop is cheaper than GPT-4o after {_get_cost_intersection(laptop_cost, llm_cost, limit, step)} papers.")
    print(
        f"Laptop + GPT-4o is cheaper than GPT-4o after "
        f"{_get_cost_intersection(laptop_llm_cost, llm_cost, limit, step)} papers."
    )

    fig = plt.figure(layout="constrained")
    grid = GridSpec(4, 3, figure=fig)
    ax4 = fig.add_subplot(grid[3, 0])
    ax4.plot(x_pos, laptop_llm_cost, lw=0.5, color=_COLORS[3])

    ax1 = fig.add_subplot(grid[0, 0], sharex=ax4)
    ax1.plot(x_pos, laptop_cost, lw=0.5, color=_COLORS[0])

    ax2 = fig.add_subplot(grid[1, 0], sharex=ax4)
    ax2.plot(x_pos, server_cost, lw=0.5, color=_COLORS[1])

    ax3 = fig.add_subplot(grid[2, 0], sharex=ax4)
    ax3.plot(x_pos, llm_cost, lw=0.5, color=_COLORS[2])

    ax5 = fig.add_subplot(grid[:, 1:])
    ax5.plot(x_pos, laptop_cost, lw=0.5, color=_COLORS[0], label="Laptop")
    ax5.plot(x_pos, server_cost, lw=0.5, color=_COLORS[1], label="Server")
    ax5.plot(x_pos, llm_cost, lw=0.5, color=_COLORS[2], label="GPT-4o")
    ax5.plot(x_pos, laptop_llm_cost, lw=0.5, color=_COLORS[3], label="Laptop + GPT-4o")
    ax5.legend(loc="upper left")

    # add zoom onto server price structure
    x_steps = 20
    x_index = math.ceil(len(server_cost) * 3 / 5)
    x_value = x_index * (limit // step)
    zoom_start, zoom_end = x_value - (x_steps * (limit // step)), x_value + (x_steps * (limit // step))
    axins = inset_axes(ax2, width="30%", height="30%", loc="lower right")
    axins.plot(x_pos, server_cost, lw=0.5, color=_COLORS[1])
    axins.set_xlim(zoom_start, zoom_end)
    axins.set_ylim(server_cost[x_index - x_steps], server_cost[x_index + x_steps])
    mark_inset(ax2, axins, loc1=1, loc2=3, lw=0.3)
    plt.setp(axins.spines.values(), linewidth=0.5)  # thinner box

    # hide ticks and offset of shared x axes
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.setp(ax2.get_xticklabels(), visible=False)
    plt.setp(ax3.get_xticklabels(), visible=False)
    plt.setp(ax1.get_xaxis().get_offset_text(), visible=False)
    plt.setp(ax2.get_xaxis().get_offset_text(), visible=False)
    plt.setp(ax3.get_xaxis().get_offset_text(), visible=False)
    axins.set_xticks([])
    axins.set_yticks([])

    ax1.set_title("Kosten der einzelnen Methoden")
    ax5.set_title("Alle Kosten im Vergleich")
    fig.supxlabel("Anzahl an Veröffentlichungen")
    fig.supylabel("Kosten in Euro")
    fig.suptitle("Kosten der Verarbeitung von Veröffentlichungen")
    plt.savefig(util.get_stats_dir() / "CostComparison", dpi=300, bbox_inches="tight")


def _graph_ai_eval() -> None:
    # data from evaluate.py
    stats = {
        # my_stats, ai_stats
        "wrong_data": (9, 6),
        "only_names_correct": (17, 2),
        "only_affiliations_correct": (2, 0),
        "minor_mistake": (8, 2),
        "correct_data": (64, 90)
    }

    # match colors to meaning (kinda)
    colors = [
        _COLORS[3], _COLORS[1], _COLORS[4], _COLORS[0], _COLORS[2]
    ]

    fig, ax = plt.subplots()
    x_pos = np.arange(2)
    multiplier = 0
    width = 1 / (len(stats) + 1)
    for key, values in stats.items():
        offset = width * multiplier
        bars = ax.bar(x_pos + offset, values, width, label=key, color=colors[multiplier])
        ax.bar_label(bars, padding=4)
        multiplier += 1

    ax.set_ylabel("Veröffentlichungen")
    ax.set_xticks(x_pos + width * 2, ("Extraktion", "ChatGPT"))
    ax.set_title("Statistiken der Evaluation von Extraktion und ChatGPT (n = 100)")
    ax.legend(loc='upper left')
    plt.savefig(util.get_stats_dir() / "EvalAi", dpi=300, bbox_inches="tight")


def _graph_rapidfuzz_scorers() -> None:
    # data from rapidfuzz_comparison.py and manually checked for correctness
    # total: 94
    # no correct matches: 29
    #   of those not manually found on ROR: 8
    #   of those malformed extractions: 3
    #   ror name too short and thus not in ROR dataset: 1
    n = 94
    scorers = [
        # scorer name, normalized time, correct matches
        ("ratio", 0.05824490534827057, 21 / n),
        ("partial_ratio", 0.45171472113073097, 58 / n),
        ("token_set_ratio", 0.3025394599384012, 34 / n),
        ("partial_token_set_ratio", 0.007251288124597941, 1 / n),
        ("token_sort_ratio", 0.2120387492783904, 19 / n),
        ("partial_token_sort_ratio", 0.6460173282262909, 16 / n),
        ("token_ratio", 0.3646243525621189, 34 / n),
        ("partial_token_ratio", 0.009909146874207039, 1 / n),
        ("WRatio", 1.0, 60 / n)
    ]

    fig, ax = plt.subplots()
    ax.scatter(
        [s[1] for s in scorers], [s[2] for s in scorers],
        color=_COLORS[0], marker=".", alpha=0.5, edgecolors="none"
    )
    texts = []
    for i, scorer in enumerate(scorers):
        texts.append(ax.annotate(scorer[0], (scorer[1], scorer[2]), ha="center", va="bottom"))

    adjustText.adjust_text(
        texts, expand=(1.5, 2.5), force_text=(0.65, 1.0),
        arrowprops={"arrowstyle": "-", "color": _COLORS[1], "lw": 0.3}
    )

    ax.set_xlabel("Normalisierte Laufzeit")
    ax.set_ylabel("Anteil korrekter Matchings")
    ax.set_title("Korrektheit und Laufzeit der verschiedenen RapidFuzz-Scorer")
    plt.savefig(util.get_stats_dir() / "RapidfuzzScorers", dpi=300, bbox_inches="tight")


def _print_threshold_stats(combined_data: list[CombinedData], stats: Stats) -> None:
    name_matchings_passed = 0
    aff_matchings_passed = 0
    for paper in combined_data:
        matched_data = paper.matched
        if not matched_data:
            continue

        matched_authors = matched_data.matched_authors
        for author in matched_authors:
            if author.score >= _NAME_CUTOFF_SCORE:
                name_matchings_passed += 1
            for affiliation in author.affiliations:
                if affiliation.score >= _AFF_CUTOFF_SCORE:
                    aff_matchings_passed += 1

    total_names = len(stats.match_stats.author_match_scores)
    print(
        f"{name_matchings_passed} of {total_names} name matchings left with a "
        f"score threshold of {_NAME_CUTOFF_SCORE} ({name_matchings_passed / total_names * 100:.2f}%)"
    )

    total_affs = len(stats.match_stats.author_match_scores)
    print(
        f"{aff_matchings_passed} of {total_affs} affiliation matchings left with a "
        f"score threshold of {_AFF_CUTOFF_SCORE} ({aff_matchings_passed / total_affs * 100:.2f}%)"
    )


def _print_ext_author_stats(combined_data: list[CombinedData], stats: Stats) -> None:
    schemes_used = []
    for paper in combined_data:
        ext_authors = paper.ext_authors
        if not ext_authors:
            schemes_used.append(0)
        else:
            schemes_used.append(len(ext_authors.extractions))

    print(f"Papers with no used extractor: {len([p for p in schemes_used if p == 0])}")
    print(f"Papers with only one used extractor: {len([p for p in schemes_used if p == 1])}")
    print(f"Papers with multiple extractors used: {len([p for p in schemes_used if p > 1])}")
    print(f"Average used extractors per paper: {sum(schemes_used) / len(schemes_used)}")
    no_failed = [p for p in schemes_used if p != 0]
    print(f"Average used extractors per paper (ignoring failed ones): {sum(no_failed) / len(no_failed)}")
    print(f"Average of the best extraction score per paper: {np.average(stats.ext_stats.best_scores)}")


def _print_latex_file_stats() -> None:
    tex_files = util.get_all_tex_files(util.get_papers_dir(), ignore_cls=False)
    print(f"Number of LaTeX files: {len(tex_files)}")
    tex_files_size = sum(tex_file.stat().st_size for tex_file in tex_files)
    print(f"Size of LaTeX files: {tex_files_size} bytes ({tex_files_size / 1_073_741_824:.2f} GB)")


def _print_basic_stats(combined_data: list[CombinedData], stats: Stats) -> None:
    _print_latex_file_stats()
    # arxiv api response stats for affiliations
    arxiv_affiliations.main()
    _print_ext_author_stats(combined_data, stats)
    _print_threshold_stats(combined_data, stats)


def _match_stats(match_data: MatchedPaperData, match_stats: MatchStats) -> None:
    author_matches = match_data.matched_authors
    for author_match in author_matches:
        match_stats.author_match_scores.append(author_match.score)
        for aff_match in author_match.affiliations:
            match_stats.aff_match_scores.append(aff_match.score)


def _ext_stats(ext_authors: ExtAuthorInfo, ext_stats: ExtStats) -> None:
    ext_stats.inc_ext_types(ext_authors.ext_type)
    extractions = ext_authors.extractions
    best_ext = extractions[0]
    for ext in extractions:
        ext_stats.scores.append(ext.score)
        ext_stats.inc_schemes(ext.scheme_name)
        ext_stats.add_score_to_scheme(ext.scheme_name, ext.score)
        if ext.score > best_ext.score:
            best_ext = ext

    ext_stats.extracted_authors += len(best_ext.authors)
    ext_stats.best_scores.append(best_ext.score)
    ext_stats.inc_best_schemes(best_ext.scheme_name)


def _cmd_stats(ext_cmds: ExtCmdData, cmd_stats: CmdStats) -> None:
    cmd_stats.inc_doc_classes(ext_cmds.documentclasses)
    cmds = [cmd.sanitized_cmd for cmd in ext_cmds.cmds]
    cmd_stats.extracted_cmds += len(cmds)

    cmd_names = [cmd_util.get_cmd_name(cmd) for cmd in cmds]
    sorted_names = sorted(set(cmd_names))
    scmd_str = ", ".join(sorted_names)
    cmd_stats.inc_cmd_combinations(scmd_str)
    cmd_stats.inc_cmd_names(cmd_names)


def _build_stats(combined_data: list[CombinedData]) -> Stats:
    stats = Stats()
    stats.file_stats.total_papers = len(combined_data)
    for paper_data in combined_data:
        tex_dir = util.get_paper_tex_dir_by_arxiv_id(paper_data.arxiv.arxiv_id)
        tex_files = util.get_all_tex_files(tex_dir)
        if len(tex_files) == 0:
            stats.file_stats.no_latex += 1
            continue

        ext_cmds = paper_data.ext_cmds
        if not ext_cmds or not ext_cmds.cmds:
            stats.file_stats.no_cmds += 1
            continue

        _cmd_stats(ext_cmds, stats.cmd_stats)
        ext_authors = paper_data.ext_authors
        if not ext_authors:
            stats.file_stats.no_ext += 1
            continue

        _ext_stats(ext_authors, stats.ext_stats)
        match_data = paper_data.matched
        if not match_data:
            stats.file_stats.no_matched += 1
            continue

        _match_stats(match_data, stats.match_stats)

    return stats


def _build_data(paper_dirs: list[Path]) -> list[CombinedData]:
    data = []
    for paper_dir in paper_dirs:
        arxiv_metadata = util.read_json(paper_dir, util.ARXIV_METADATA_FILE)
        ext_cmds = util.read_json(paper_dir, util.CMDS_FILE)
        ext_authors = util.read_json(paper_dir, util.EXTRACTED_DATA_FILE)
        matched = util.read_json(paper_dir, util.MATCHED_DATA_FILE)
        data.append(CombinedData(arxiv_metadata, ext_cmds, ext_authors, matched))

    return data


def run(paper_dirs: list[Path]) -> None:
    util.configure_logger(_logger)
    _logger.info("Collecting data...")
    combined_data = util.read_json(util.get_stats_dir(), util.STATS_ALL_DATA)
    if not combined_data:
        _logger.info("Building data collection...")
        combined_data = _build_data(paper_dirs)
        util.write_obj_to_json(util.get_stats_dir(), util.STATS_ALL_DATA, combined_data)
        _logger.info("Saved data collection!")

    stats = util.read_json(util.get_stats_dir(), util.BASIC_STATS_FILE)
    if not stats:
        _logger.info("Building basic stats...")
        stats = _build_stats(combined_data)
        util.write_obj_to_json(util.get_stats_dir(), util.BASIC_STATS_FILE, stats)
        _logger.info("Saved basic stats!")

    _logger.info("Printing some basic stats...")
    _print_basic_stats(combined_data, stats)

    _logger.info("Painting graphs...")
    plt.rcParams['font.size'] = 6
    # static data
    _graph_rapidfuzz_scorers()
    _graph_ai_eval()
    _graph_ext_cost()

    # stats
    _graph_funnel_file_stats(stats)
    _graph_most_used_doc_classes(stats)
    _graph_most_used_cmd_names(stats)
    _graph_most_used_cmd_combinations(stats)
    _graph_ext_scores(stats)
    _graph_best_ext_scores(stats)
    _graph_ext_scores_by_scheme(stats)
    _graph_scores_by_scheme_occ(stats)
    _graph_name_scores_and_aff_scores(stats)

    # # combined data
    _graph_best_ext_scores_over_time(combined_data)

    # # filtered data
    filtered_papers = _filter_by_cutoff(combined_data)
    _print_basic_author_stats(filtered_papers)
    _graph_top_authors(filtered_papers)
    _graph_top_affiliations(filtered_papers)

    # generate data for external stats processing
    _logger.info("Generating export datasets...")
    _generate_fg_dataset_institution(filtered_papers)
    _generate_fg_dataset_country(filtered_papers)
    _save_fgi_html()
    _save_fgw_html()


def main():
    util.clear_stats()
    run(util.get_paper_dirs())


if __name__ == "__main__":
    main()
