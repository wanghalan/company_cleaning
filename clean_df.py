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
        "[^0-9a-zA-Z]+", " ", s
    ).strip()  # remove all nonalphanumeric, and removes leading and trailing zeros
    s = " ".join(s.split())  # remove etra white spaces in the middle
    s = s.lower()  # to lower case
    return s


def filter_company_name(cleaned_company_name):
    endings = {
        "labs",
        "ventures",
        "solutions",
        "partners",
        "holdings",
        "son",
        "co",
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
        "companies",
        "company",
        "creative",
        "productions",
        "prod",
    }
    if cleaned_company_name.split(" ")[-1] in endings:
        return " ".join(cleaned_company_name.split(" ")[:-1])
    else:
        return cleaned_company_name


def prep_states_info():
    us_states_df = pd.read_csv("us_states.csv")
    us_states_df["State"] = us_states_df["State"].map(clean_str)
    us_states_df["Standard"] = us_states_df["Standard"].map(clean_str)
    us_states_df["Postal"] = us_states_df["Postal"].map(clean_str)
    return us_states_df


def filter_states_info(cleaned_company_name, states):
    if cleaned_company_name.split(" ")[-1] in states:
        return " ".join(cleaned_company_name.split(" ")[:-1])
    else:
        return cleaned_company_name


def check_same_name(company_a, company_b, lcp_cutoff=5):
    """
    For each token in the company name, if both companies have character remains after filtering for normal words, if the intersection of non-english words is > 0 return True
    """

    # check for exact subset of string space removed
    if "".join(company_a.split()) in "".join(company_b.split()) or "".join(
        company_b.split()
    ) in "".join(company_a.split()):
        return True

    d = set(words.words())
    a = set(company_a.split(" "))
    b = set(company_b.split(" "))

    remain_a = set(a) - set(d)
    remain_b = set(b) - set(d)

    # check for longest_common_substrings > 5 after removing dictionary names
    lcp = os.path.commonprefix(["".join(sorted(remain_a)), "".join(sorted(remain_a))])
    if len(lcp) > lcp_cutoff:
        return True
    # logging.debug(remain_a)
    # logging.debug(remain_b)
    answer = False

    # if either company retains words after you subtract the normal dictionary
    if len(remain_a) > 0 and len(remain_b) > 0:
        intersect = remain_a.intersection(remain_b)
        logging.debug("\t\t[%s]: %s" % (len(intersect), intersect))
        logging.debug(remain_a)
        logging.debug(remain_b)
        logging.debug(remain_a ^ remain_b)
        # if size of the intersection is the whole word for at least one of the company names, return True
        if len(intersect) > 0:
            answer = True
        elif "".join(remain_a) in "".join(remain_b) or "".join(remain_b) in "".join(
            remain_a
        ):
            answer = True

    return answer


if __name__ == "__main__":
    # logging.debug(filter_company_name("coca cola co"))
    # logging.debug(filter_company_name("coca cola"))
    # logging.debug(filter_company_name("great lakes brewing company"))
    # logging.debug(filter_company_name("boston bears co"))
    states_df = prep_states_info()
    states = itertools.chain(
        states_df["State"], states_df["Standard"], states_df["Postal"]
    )
    # logging.debug(filter_states_info("coca cola fl", states))

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
    df["cleaned"] = df[args.column].map(clean_str)
    df["cleaned"] = df["cleaned"].apply(lambda x: filter_states_info(x, states))
    df["cleaned"] = df["cleaned"].map(filter_company_name)

    companies = list(df["cleaned"].unique())
    # companies = companies[:100]  # small test
    starting_size = len(companies)

    logging.debug("Length of cleaned companies: %s" % len(companies))

    logging.debug("Starting company matches")

    company_dict = {
        # company_name: set(different_company varaitions, variation2, variation3, ...)
    }

    start_length = len(companies)
    with tqdm(total=start_length) as pbar:
        while len(companies) > 0:
            target_company = companies.pop(0)
            company_dict[target_company] = [target_company]
            pbar.set_description("Target company:\t%s" % target_company)

            # now for all remaining companies, check if the company matches the company dictionary
            for i in range(len(companies)):
                candidate_company = companies.pop(0)
                # logging.debug("candidate company: %s" % candidate_company)
                # pbar.set_description("Checking:\t%s" % candidate_company)
                matched = False
                if fuzz.ratio(target_company, candidate_company) > 80:
                    logging.debug(
                        "Found candidate: (%s,%s) --> %s"
                        % (
                            target_company,
                            candidate_company,
                            check_same_name(target_company, candidate_company),
                        )
                    )
                    if check_same_name(target_company, candidate_company):
                        company_dict[target_company].append(candidate_company)
                        logging.debug(company_dict[target_company])
                        logging.debug(
                            "\t[%s] new match found (%s,%s)"
                            % (
                                len(company_dict[target_company]),
                                target_company,
                                candidate_company,
                            )
                        )
                        matched = True
                if not matched:  # add it back into the original list
                    companies.append(candidate_company)
            pbar.update(start_length - 1)

    logging.debug(company_dict)
    reduced = pd.DataFrame.from_dict(company_dict, orient="index")
    logging.debug(reduced)
    reduced.to_csv(args.output_file, index=False)
