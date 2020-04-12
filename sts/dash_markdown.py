introduction = """## Introduction

On 1 January 2019, the [Securitisation Regulation](https://eur-lex.europa.eu/legal-content/en/TXT/?uri=celex:32017R2402) came into force in the European Union (EU).  The Securitisation Regulation created a new regulatory regime for securitisations in Europe.  Among other things, it created a new category of securitisations, known as "simple, transparent and standardised" (STS) securitisations.  Securitisations can be classified as STS if they meet certain requirements set out in the Securitisation Regulation (as supplemented by various delegated rules and technical standards).  Investments in STS securitisations receive preferential capital treatment under the EU's capital requirements regulations, reflecting the fact that STS securitisations are considered to be safer than non-STS securitisations.

Broadly speaking, a "securitisation" is a transaction involving the establishment of a special-purpose company or similar legal entity (often referred to as the *issuer*) to acquire assets (such as loans, mortgages, lease receivables, trade receivables, etc) from one or more third parties (referred to as *originators*).  The issuer funds its acquisition of the assets by issuing debt securities (often referred to as *notes*) to investors, and payments of principal and interest on the notes are in turn funded by the amounts that the issuer receives in respect of the underlying assets.  The Securitisation Regulation applies to securitisations which involve the tranching of credit risk, ie, where the issuer issues different tranches of notes and, in the event that some of the underlying assets underperform, the more "junior" tranches of notes will incur losses before the more "senior" tranches.  

More information about the Securitisation Regulation and the STS regime can be found on [the website of the European Securities and Markets Authority (ESMA)](https://www.esma.europa.eu/policy-activities/securitisation)

When a securitisation is notified to ESMA as being an STS securitisation, ESMA publishes certain details about that securitisation on its website.  Those details are currently published as [a spreadsheet](https://www.esma.europa.eu/policy-activities/securitisation/simple-transparent-and-standardised-sts-securitisation).  This page visualises some of the data that ESMA has published about STS securitisations.  Of course, there are many securitisations which are not STS securitisations, and they are not discussed here.  On this page, where we refer to securitisations, we are referring specifically to STS securitisations.

Unless stated otherwise, the data visualised here ranges from the beginning of 2019 to the end of March 2020.

You should also bear in mind that the charts on this page give a breakdown of STS securitisations by *number* of securitisations; ESMA does not publish information about the size of each securitisation, so the below charts do not say anything about the *value* of assets that have been securitised.

"""

stss_count = """## Number of STS securitisations

Below you can see the cumulative number of notified STS securitisations over the time period, as well as the number of new STS securitisations that were notified to ESMA each month.  During this time period, **{stss_count}** securitisations were notified to ESMA as being STS securitisations.  As you can see, although the Securitisation Regulation came into force on 1 January 2019, the first STS securitisations did not take place until March 2019.
"""

asset_classes_pie = """## Underlying assets

ESMA publishes information about the types of underlying assets that have been securitised.  You can see the breakdown in the pie chart below.  Auto loans and leases are the asset class most commonly securitised in STS securitisations, followed by trade receivables and then by residential mortgages.
"""

new_by_ac = """The below bar chart demonstrates how many new STS securitisations in each month involved each asset class."""

stss_by_abcp = """## Asset-backed commercial paper

An asset-backed commercial paper (ABCP) transaction is a particular type of short-term securitisation, where the notes issued by the issuer have a maturity of less than one year.  Typically, ABCP transactions involve issuing short-term notes (known as commercial paper) on a "rolling" basis, ie, issuing new commercial paper to fund the repayment of old commercial paper as it matures.  Due to their short-term nature, the Securitisation Regulation applies slightly different rules to ABCP transactions and programmes than to other securitisations.

As you can see, the majority of STS securitisations in this time period have been non-ABCP transactions."""

ac_by_abcp = """Breaking down the ABCP status of securitisations by asset class, you can see that trade receivables securitisations have all been ABCP transactions, possibly reflecting the fact that trade recevables (debts due to companies in the course of their trade) themselves tend to be short-term assets.  Securitisations of residential mortgages (being longer-term assets) have all been non-ABCP transactions, whereas auto loan and lease securitisations are a mix of ABCP and non-ABCP transactions."""

private_public = """## Private and public STS securitisations

The Securitisation Regulation and the associated technical standards distinguish between public securitisations (in respect of which a prospectus must be drawn up under the EU's Prospectus Regulation) and private securitisations.  ESMA publishes extensive details on public STS securitisations, such as details of the parties involved, certain details of the transaction documents, etc.  By contrast, although details of private STS securitisations must be notified to ESMA, only a small subset of those details are published on ESMA's website, such as the nature of the underlying assets being securitised.

As you can see from the below pie chart, just over half of the STS securitisations notified to ESMA in this time period have been public securitisation.

Because of the limited amount of information available about private STS securitisations, most of the rest of this page will focus on public STS securitisations only (unless otherwise stated).  The sections above, discussing the asset classes and ABCP status of STS securitisations, cover all STS securitisations (public and private).
"""

stss_by_oc = """## Originator countries

Below you can see a pie chart (and below that, a "heatmap" of Europe) showing how many STS securitisations involved originators from each country.  The UK tops this list, with about a third of all STS securitisations involving an originator from that country."""

oc_vs_gdp = """If we plot the number of securitisations involving originators from a country against that country's GDP, we can see a moderate positive correlation between the size of a country's economy and the number of STS securitisations involving originators from that country (Pearson correlation coefficient of **{corr}**).  The Netherlands and the United Kingdom stand out as having an unusually large number of STS securitisations relative to their GDP."""

ac_by_oc = """Below you will find a bar chart showing what asset classes were securitised by originators for each country.  You can see, for example, that in the UK and the Netherlands, residential mortgage securitisations are the most common, whereas in Germany, auto loans and leases are the most commonly securitised asset class."""

new_by_oc = """And the below bar chart breaks down the number of new securitisations per month by country of originator."""

oc_vs_ic = """## Issuer data

The data published by ESMA includes certain details (including country) of the *originators* in respect of each STS securitisation, but it does not currently include details of the *issuers* (which may be based in different countries to the respective originators).  However, where debt securities are listed on a stock exchange in the European Economic Area (EEA), the exchange is required, under the [Markets in Financial Instruments Regulation](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32014R0600), to submit details of those debt securities to ESMA.  ESMA publishes that data in its [Financial Instrument Reference Data System](https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_firds) (FIRDS).  By cross-referencing the International Securities Identification Numbers (ISINs) associated with public securitisations against FIRDS data, we are able to piece together some additional information about the relevant securities and the entities that issue them.

The below table of "Issuer Countries" against "Originator Countries" demonstrates the relationship between the issuer jurisdictions and the originator jurisdictions.  As you can see, for most public STS securitisations, the issuer is based in the same jurisdiction as the originator, but this is not always the case."""

diff_by_ic = """Of those securitisations where the originator and the issuer are not based in the same country, most of them have a German originator and a Luxembourg issuer.  The below pie chart demonstrates the prevalence of Luxembourg as an issuer jurisdiction for public STS securitisations."""

stss_by_currency = """## Currency of notes

Finally, we break down the public STS securitisations by the Dcurrency in which the notes are denominated.  About two thirds of all public STS securitisations are denominated in EUR."""

oc_by_currency = """The below bar chart shows the relationship between the currencies that STS securitisations are denominated in and the countries in which the underlying originators are based.  As you might expect, most securitisations are denominated in the national currency of the underlying originator, though this is not always the case.  Note that just because an originator is located in a country, does not mean that the underlying assets being securitised are necessarily denominated in that country's currency (for example, a securitisation could involve GBP-denominated loans originated by an Irish originator).  Where there is a mis-match between the currency of the STS securitisation and the currency of the underlying assets, the currency risk arising from this mis-match must be appropriately mitigated, such as through foreign exchange hedging agreements, pursuant to Article 21(2) of the Securitisation Regulation."""

sources = """## Data sources

Data on STS securitisations obtained from ESMA's webpage at https://www.esma.europa.eu/policy-activities/securitisation/simple-transparent-and-standardised-sts-securitisation.

GDP data obtained from Eurostat's website at https://ec.europa.eu/eurostat/databrowser/view/tec00001/default/table?lang=en (published by the EU under a [CC BY 4.0 licence](https://creativecommons.org/licenses/by/4.0/#)).

Geodata for the heatmap obtained from Eurostat's website at https://ec.europa.eu/eurostat/web/gisco/geodata/reference-data/administrative-units-statistical-units/countries.  © EuroGeographics for the administrative boundaries.

FIRDS data obtained from ESMA's FIRDS files register at https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_firds_files.

Certain data about issuers obtained from the website of the Global Legal Entity Identifier Foundation (GLEIF) at https://www.gleif.org/en/lei-data/gleif-lei-look-up-api/access-the-api/.

This page was built in the [Python](https://www.python.org/) programming language using [Pandas](https://pandas.pydata.org/) and [Plotly / Dash](https://plotly.com/dash/), among other tools.  The source code used to generate this website can be found [here](https://github.com/bunburya/data_analysis/tree/master/sts) and is made available under the MIT licence."""

