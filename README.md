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
4. We itereate across the companies and check for fuzzy matches. For any match > 80%, we check the resulting match and remove from them the list of common words in the english dictionary. If after the removal a name remains in both, we check for the intersection of the two remaining sets. Of those, if the length of the total intersection characters is greater than the lenght of characters in the disjoint set, and the disjoint set size is zero, we return the shorter of the two company names
```python
def non_normal_majority_merging(company_a, company_b):
    """
    For each token in the company name, if both companies have character remains after filtering for normal words, if the intersection of non-english words is > 0 return True
    """
    d = set(words.words())
    a = set(company_a.split(" "))
    b = set(company_b.split(" "))

    remain_a = set(a) - set(d)
    remain_b = set(b) - set(d)

    if len(remain_a) <= 0 or len(remain_b) <= 0:
        return False, None
    else:
        # check for intersection. If the total words in the intersection characters is greater than the mean of the disjoint character sum, return True
        intersect = remain_a.intersection(remain_b)
        disjoint = remain_a ^ remain_b

        int_s = "".join(intersect)
        dis_s = "".join(disjoint)

        if len(int_s) > len(dis_s) and len(dis_s) == 0:
            return True, min([company_a, company_b], key=len)
        else:
            return False, None
```

In the main function, we iterate across an example companies list once to see the results:
```python
    # Testing the filters
    print(filter_company_name("coca cola co"))
    print(filter_company_name("coca cola"))
    states_df = prep_states_info()
    states = itertools.chain(
        states_df["State"], states_df["Standard"], states_df["Postal"]
    )
    print(filter_states_info("coca cola fl", states))

    # Testing the final set of company names
    df = pd.read_csv("QnA_Labeled_Food_Companies_2017_companies.csv")
    print(df.columns)
    # remove nonalphanumeric
    df["cleaned"] = df["qa_company_1"].map(clean_str)
    # remove states from the end of the name
    df["cleaned"] = df["cleaned"].apply(lambda x: filter_states_info(x, states))
    # remove common company endings from the end of the name
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
```
