from tracemalloc import start
import pandas as pd
from tqdm import tqdm
import re
import nltk
from nltk.corpus import words
import itertools
from fuzzywuzzy import fuzz
import argparse
import json
import logging
import os

# nltk.download('words')


def clean_str(s, replace=" "):
    s = re.sub(
        r"[^A-Za-z0-9 ]+", "", s
    ).strip()  # remove all nonalphanumeric, and removes leading and trailing zeros
    s = " ".join(s.split())  # remove etra white spaces in the middle
    return s


def filter_company_name(cleaned_company_name):
    endings = {
        "labs",
        "bio",
        "biotech",
        "laboratories",
        "ventures",
        "solutions",
        "sciences",
        "partners",
        "holdings",
        "son",
        "co",
        "corp",
        "corporation",
        "inc",
        "incorporated",
        "brothers",
        "tech",
        "foods",
        "books",
        "industrial",
        "innovations",
        "bureau",
        "prestige",
        "worldwide",
        "international",
        "direct",
        "online",
        "properties",
        "pharm",
        "pharms",
        "pharma",
        "usa",
        "development",
        "technologies",
        "consulting",
        "works",
        "unlimited",
        "specialties",
        "scintific",
        "digital",
        "brands",
        "logistics",
        "llc",
        "ltd",
        "companies",
        "company",
        "creative",
        "productions",
        "prod",
    }
    return " ".join([v for v in cleaned_company_name.split(" ") if not v in endings])


def prep_states_info():
    us_states_df = pd.read_csv("us_states.csv")
    us_states_df["State"] = us_states_df["State"].map(clean_str)
    us_states_df["Standard"] = us_states_df["Standard"].map(clean_str)
    us_states_df["Postal"] = us_states_df["Postal"].map(clean_str)
    states = itertools.chain(
        us_states_df["State"], us_states_df["Standard"], us_states_df["Postal"]
    )
    return states


def filter_states_info(cleaned_company_name, states):
    return " ".join([v for v in cleaned_company_name.split(" ") if not v in states])


def get_words():
    return set(words.words())


def filter_common_words(company_name, words, length_cutoff=3):
    tokens = company_name.split(" ")
    blanket = " ".join([v for v in tokens if not v in words or len(v)])
    if (
        len(blanket) == 0
    ):  # if the entirety of the word is removed, return a substring up to a token of the cutoff
        answer = []
        for token in tokens:
            if len(token) >= length_cutoff:
                answer.append(token)
                break
            else:
                answer.append(token)
        return " ".join(answer)
    else:
        return blanket


def check_same_name(company_a, company_b, lcp_cutoff=5):
    """
    For each token in the company name, if both companies have character remains after filtering for normal words, if the intersection of non-english words is > 0 return True
    """

    d = set(words.words())
    a = set(company_a.split(" "))
    b = set(company_b.split(" "))

    remain_a = set(a) - set(d)
    remain_b = set(b) - set(d)

    # if either company retains words after you subtract the normal dictionary
    if len(remain_a) > 0 and len(remain_b) > 0:
        intersect = remain_a.intersection(remain_b)
        logging.debug("\t\t[%s]: %s" % (len(intersect), intersect))
        logging.debug(remain_a)
        logging.debug(remain_b)
        logging.debug(remain_a ^ remain_b)
        # if size of the intersection is the whole word for at least one of the company names, return True
        if len(intersect) > min([len(a), len(b)]) + 1:
            return True
        elif "".join(remain_a) in "".join(remain_b) and "".join(remain_b) in "".join(
            remain_a
        ):
            return True

    return False


def get_shortest_non_empty(*args):
    return min([v for v in list(args) if len(v) > 0])


def clean(df, default_col="name", keep_process=False):
    # prep dictionary of information
    states = prep_states_info()
    common_words = get_words()

    df = df.dropna()
    df["name"] = df[default_col].str.lower()
    df["clean"] = df["name"].map(clean_str)
    df["-company"] = df["clean"].map(filter_company_name)
    df["-states"] = df["-company"].apply(lambda x: filter_states_info(x, states))

    df["-common"] = df["-states"].apply(lambda x: filter_common_words(x, common_words))
    df["short"] = df.apply(
        lambda row: get_shortest_non_empty(
            row["name"], row["clean"], row["-company"], row["-states"], row["-common"]
        ),
        axis=1,
    )
    if not keep_process:
        ndf = pd.DataFrame()
        ndf["name"] = sorted(list(df["short"].unique()))
        return ndf
    else:
        return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compress a set of company names")
    parser.add_argument(
        "-i",
        "--input_file",
        type=str,
        help="The data frame in csv that needs to be audited",
        required=True,
    )
    parser.add_argument(
        "-c",
        "--column",
        type=str,
        help="The column in the data frame to analyze",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output_file",
        type=str,
        default="company_rep.csv",
        help="The path of the file to output",
    )
    parser.add_argument("-v", "--verbose", action=argparse.BooleanOptionalAction)

    args = parser.parse_args()
    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG

    logging.basicConfig(format="%(levelname)s: %(message)s", level=log_level)

    df = pd.read_csv(args.input_file)
    logging.info("Columns: %s" % df.columns)
    logging.info(df)
    starting_size = len(df)

    df = clean(df, args.column)
    companies = list(df["name"].unique())
    # companies = companies[:100]  # small test
    logging.debug("Length of cleaned companies: %s" % len(companies))

    logging.debug("Starting company matches")

    # company_dict = {
    #     # company_name: set(different_company varaitions, variation2, variation3, ...)
    # }

    # start_clean_size = len(companies)
    # i = 0
    # with tqdm(total=int((start_clean_size * (start_clean_size - 1)) / 2)) as pbar:
    #     while len(companies) > 0:
    #         i += 1
    #         target_company = companies.pop(0)
    #         company_dict[target_company] = [target_company]
    #         pbar.set_description("Target company:\t%s" % target_company)

    #         # now for all remaining companies, check if the company matches the company dictionary
    #         for i in range(len(companies)):
    #             candidate_company = companies.pop(0)
    #             # logging.debug("candidate company: %s" % candidate_company)
    #             # pbar.set_description("Checking:\t%s" % candidate_company)
    #             matched = False
    #             if fuzz.ratio(target_company, candidate_company) > 80:
    #                 logging.debug(
    #                     "Found candidate: (%s,%s) --> %s"
    #                     % (
    #                         target_company,
    #                         candidate_company,
    #                         check_same_name(target_company, candidate_company),
    #                     )
    #                 )
    #                 if check_same_name(target_company, candidate_company):
    #                     company_dict[target_company].append(candidate_company)
    #                     logging.debug(company_dict[target_company])
    #                     logging.debug(
    #                         "\t[%s] new match found (%s,%s)"
    #                         % (
    #                             len(company_dict[target_company]),
    #                             target_company,
    #                             candidate_company,
    #                         )
    #                     )
    #                     matched = True
    #             if not matched:  # add it back into the original list
    #                 companies.append(candidate_company)
    #         pbar.update(start_clean_size - len(companies))

    # logging.debug(company_dict)
    # reduced = pd.DataFrame.from_dict(company_dict, orient="index")
    reduced = pd.DataFrame()
    reduced["name"] = sorted(companies)
    logging.info(reduced)
    reduced.to_csv(args.output_file, index=False)
    logging.info("-" * 80)
    logging.info(
        "Reduction: %.2f" % (((starting_size) - len(companies)) / starting_size)
    )
    logging.info("Final size: %s" % len(reduced))
