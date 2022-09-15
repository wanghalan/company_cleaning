# company_cleaning

Sometimes given sets of company names, they refer to the same company even though the name is different. In this repository, we use 4 approaches to consolidate these strings:

1. Remove non-alphanumeric characters, remove leading and trailing white space, and remove duplicate white space in the middle
```python
def clean_str(s, replace=" "):
    s = re.sub(
        "[^0-9a-zA-Z]+", " ", s
    ).strip()  # remove all nonalphanumeric, and removes leading and trailing zeros
    s = " ".join(s.split())  # remove etra white spaces in the middle
    s = s.lower()  # to lower case
    return s
```


2. We remove common state names from the end of a file
```python
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
```

3. We remove common company names from the string:
```python
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
```
4. We check for same names aggressively in a series of checks: 1) if after reduction the string is exactly a subset of one or the other, 2) whether after removing normal dictionary terms there still exists an intersection, and 3) after removal, if the string removing white space is the subset of one or the other
```python
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
```

In the main function, we iterate across an example companies popping one at a time until empty. Furthermore, for each remaining, we pop the candidate to see if it matches, and leave it removed if a match is found to further reduce the runtime. A couple of re-runs do occur, but so far the damage on the second run is minimal and we keep it about n^2 in the worst case scenario.

```python
    # Load in and return a set of companies
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
```

Given the example data set, we achieved a 58% reduction in the number of companies, from 4652 companies down to -> 2240)
