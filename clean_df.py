import pandas as pd
from tqdm import tqdm
import re
import nltk
from nltk.corpus import words
import itertools
from fuzzywuzzy import fuzz

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
        "inc",
        "brothers",
        "tech",
        "foods",
        "books",
        "industrial",
        "innovations",
        "bureau",
        "prestige",
        "worldwide",
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


def non_normal_majority_merging(company_a, company_b):
    """
    For each token in the company name, if both companies have character remains after filtering for normal words, if the intersection of non-english words is > 0 return True
    """
    d = set(words.words())
    a = set(company_a.split(" "))
    b = set(company_b.split(" "))

    remain_a = set(a) - set(d)
    remain_b = set(b) - set(d)

    # print(remain_a)
    # print(remain_b)

    if len(remain_a) <= 0 or len(remain_b) <= 0:
        return False, None
    else:
        # check for intersection. If the total words in the intersection characters is greater than the mean of the disjoint character sum, return True
        intersect = remain_a.intersection(remain_b)
        disjoint = remain_a ^ remain_b

        int_s = "".join(intersect)
        dis_s = "".join(disjoint)
        #         print(intersect)
        #         print('intersect: %s' % int_s)
        #         print('disjoint: %s' % dis_s)
        if len(int_s) > len(dis_s) and len(dis_s) == 0:
            return True, min([company_a, company_b], key=len)
        else:
            return False, None


if __name__ == "__main__":
    print(filter_company_name("coca cola co"))
    print(filter_company_name("coca cola"))
    states_df = prep_states_info()
    states = itertools.chain(
        states_df["State"], states_df["Standard"], states_df["Postal"]
    )
    print(filter_states_info("coca cola fl", states))

    df = pd.read_csv("QnA_Labeled_Food_Companies_2017_companies.csv")
    print(df.columns)
    df["cleaned"] = df["qa_company_1"].map(clean_str)
    df["cleaned"] = df["cleaned"].apply(lambda x: filter_states_info(x, states))
    df["cleaned"] = df["cleaned"].map(filter_company_name)
    companies = list(df["cleaned"].unique())

    starting_size = len(companies)

    print("Length of cleaned companies: %s" % len(companies))
    for i in tqdm(range(len(companies))):
        for j in range(len(companies)):
            if i != j and fuzz.ratio(companies[i], companies[j]) > 80:
                found, name = non_normal_majority_merging(companies[i], companies[j])
                if found:
                    print(
                        "merge found: (%s, %s) --> %s"
                        % (companies[i], companies[j], name)
                    )
                    companies[i] = name
                    companies[j] = name

    print("List of merged companies: %s" % len(set(companies)))
    print("Total companies reduced: %s" % (len(set(companies)) - starting_size))
