from tracemalloc import start
import pandas as pd
from tqdm import tqdm
import re
import nltk
from nltk.corpus import words
import itertools
from fuzzywuzzy import fuzz
from pprint import pprint

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


def check_same_name(company_a, company_b):
    """
    For each token in the company name, if both companies have character remains after filtering for normal words, if the intersection of non-english words is > 0 return True
    """

    # check for subset of string space removed
    if "".join(company_a.split()) in "".join(company_b.split()) or "".join(
        company_b.split()
    ) in "".join(company_a.split()):
        return True

    d = set(words.words())
    a = set(company_a.split(" "))
    b = set(company_b.split(" "))

    remain_a = set(a) - set(d)
    remain_b = set(b) - set(d)

    # print(remain_a)
    # print(remain_b)
    answer = False

    # if either company retains words after you subtract the normal dictionary
    if len(remain_a) > 0 and len(remain_b) > 0:
        intersect = remain_a.intersection(remain_b)
        print("\t\t[%s]: %s" % (len(intersect), intersect))
        print(remain_a)
        print(remain_b)
        print(remain_a ^ remain_b)
        # if size of the intersection is the whole word for at least one of the company names, return True
        if len(intersect) > 0:
            answer = True
        elif "".join(remain_a) in "".join(remain_b) or "".join(remain_b) in "".join(
            remain_a
        ):
            answer = True

    return answer


if __name__ == "__main__":
    print(filter_company_name("coca cola co"))
    print(filter_company_name("coca cola"))
    print(filter_company_name("great lakes brewing company"))
    print(filter_company_name("boston bears co"))
    states_df = prep_states_info()
    states = itertools.chain(
        states_df["State"], states_df["Standard"], states_df["Postal"]
    )
    print(filter_states_info("coca cola fl", states))

    df = pd.read_csv("QnA_Labeled_Food_Companies_2017_companies_roberta.csv")
    print(df.columns)
    df["cleaned"] = df["qa_company_1"].map(clean_str)
    df["cleaned"] = df["cleaned"].apply(lambda x: filter_states_info(x, states))
    df["cleaned"] = df["cleaned"].map(filter_company_name)

    companies = list(df["cleaned"].unique())
    # companies = companies[:100]  # small test
    starting_size = len(companies)

    print("Length of cleaned companies: %s" % len(companies))

    print("Starting company matches")

    company_dict = {
        # company_name: set(different_company varaitions, variation2, variation3, ...)
    }

    start_length = len(companies)
    with tqdm(total=start_length * start_length) as pbar:
        while len(companies) > 0:
            target_company = companies.pop(0)
            company_dict[target_company] = [target_company]
            pbar.set_description("Target company:\t%s" % target_company)

            # now for all remaining companies, check if the company matches the company dictionary
            for i in range(len(companies)):
                candidate_company = companies.pop(0)
                # print("candidate company: %s" % candidate_company)
                # pbar.set_description("Checking:\t%s" % candidate_company)
                matched = False
                if fuzz.ratio(target_company, candidate_company) > 80:
                    print(
                        "Found candidate: (%s,%s) --> %s"
                        % (
                            target_company,
                            candidate_company,
                            check_same_name(target_company, candidate_company),
                        )
                    )
                    if check_same_name(target_company, candidate_company):
                        company_dict[target_company].append(candidate_company)
                        print(company_dict[target_company])
                        print(
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
            pbar.update(start_length - len(companies))

    pprint(company_dict)
    reduced = pd.DataFrame.from_dict(company_dict, orient="index")
    print(reduced)
    reduced.to_csv("company_rep.csv", index=False)
