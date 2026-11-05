"""
Synthetic dataset generator for the Intelligent Academic Issue Classification
project.

This is a ONE-TIME, standalone script -- it is intentionally separate from
ml/train_classifier.py. Run it once to (re)produce
ml/dataset/academic_issue_dataset.csv; the training script then loads that
CSV as a fixed artifact, so training runs stay reproducible even though this
generator uses randomness.

Design approach
----------------
Rather than hand-writing ~1,500 individual sentences (slow, error-prone, and
in practice no less "templated" than a good generator), this script builds a
large pool of hand-authored sentence *skeletons* per category (20-30 each,
covering statements, questions, requests, complaints, appeals, formal and
informal register, and Nigerian pidgin-inflected phrasing), then combines
each skeleton with randomly sampled course codes, sessions, levels,
departments, optional tone openers/closers, and light informal text
transformations. With ~25 skeletons x dozens of slot-filler combinations per
category, the combinatorial space is far larger than the ~125 examples drawn
from it, so duplicates are rare and are explicitly filtered out via a
global "seen" set (regenerating on collision) to guarantee every row in the
final CSV is a unique string.

Run:
    python ml/generate_dataset.py
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

OUTPUT_PATH = Path(__file__).resolve().parent / "dataset" / "academic_issue_dataset.csv"

# Examples per category. All fall inside the requested 120-150 range and sum
# to the ~1,500 target.
EXAMPLES_PER_CATEGORY = 125

CATEGORIES = [
    "Missing Result",
    "Grade Dispute",
    "Course Registration",
    "Transcript Request",
    "Academic Clearance",
    "Examination Issue",
    "School Fees Issue",
    "Portal/System Issue",
    "Admission Issue",
    "Certificate Collection",
    "Student Welfare",
    "Other",
]

# ---------------------------------------------------------------------------
# Shared vocabulary pools used to fill placeholders in the templates below.
# ---------------------------------------------------------------------------

COURSE_PREFIXES = [
    "CSC", "MTH", "GST", "PHY", "CHM", "ENG", "ECO", "ACC", "BUS", "STA",
    "EEE", "MEE", "CVE", "BIO", "POL", "PSY", "PHI", "ENT", "LAW", "MAC",
    "GNS", "FRN", "GEO", "SOC", "AGR", "ARC", "BCH", "MCB", "PCS", "URP",
]
COURSE_NUMBERS = [
    "101", "102", "111", "112", "121", "122", "201", "202", "211", "212",
    "221", "222", "301", "302", "311", "312", "321", "322", "401", "402",
    "411", "412",
]

def _course_code() -> str:
    return f"{random.choice(COURSE_PREFIXES)}{random.choice(COURSE_NUMBERS)}"

SESSIONS = [
    "2021/2022", "2022/2023", "2023/2024", "2024/2025",
    "last session", "this session", "last semester", "this semester",
    "the first semester", "the second semester",
]
LEVELS = [
    "100 level", "200 level", "300 level", "400 level", "500 level",
    "ND1", "ND2", "HND1", "HND2",
]
DEPARTMENTS = [
    "Computer Science", "Mass Communication", "Accounting",
    "Mechanical Engineering", "Economics", "Biochemistry", "Law",
    "Political Science", "Physics", "Statistics", "Microbiology",
    "Architecture", "Business Administration", "English",
]
COURSES_LONGFORM = [
    "Computer Science", "Accounting", "Mass Communication", "Economics",
    "Civil Engineering", "Law", "Microbiology", "Architecture",
    "Business Administration", "Political Science",
]
FEE_AMOUNTS = ["₦25,000", "₦45,000", "₦68,500", "₦120,000", "₦150,000", "₦32,750"]

def _placeholders() -> dict:
    a, b = random.sample(COURSES_LONGFORM, 2)
    return {
        "code": _course_code(),
        "code2": _course_code(),
        "session": random.choice(SESSIONS),
        "level": random.choice(LEVELS),
        "dept": random.choice(DEPARTMENTS),
        "courseA": a,
        "courseB": b,
        "amount": random.choice(FEE_AMOUNTS),
    }

# ---------------------------------------------------------------------------
# Optional tone openers / closers, applied probabilistically on top of a
# chosen skeleton so the same skeleton can still read very differently.
# ---------------------------------------------------------------------------

OPENERS_FORMAL = [
    "I wish to formally report that",
    "I am writing to bring to your attention that",
    "Kindly note that",
    "I would like to officially report that",
    "This is to notify the appropriate office that",
    "I am reaching out to inform you that",
]
OPENERS_POLITE = [
    "Please help,",
    "Good day, please,",
    "Good day ma, please,",
    "Good day sir, please,",
    "Hello, please,",
    "I hope this message finds you well.",
]
OPENERS_FRUSTRATED = [
    "I'm really frustrated because",
    "This is so frustrating -",
    "I have complained about this several times and",
    "It has been weeks and",
    "I don't understand why",
    "Honestly, I'm tired of explaining that",
]
OPENERS_PIDGIN = [
    "Abeg,",
    "Pls I beg,",
    "E don tey I dey try this thing,",
    "I don try everything but",
]

CLOSERS = [
    "Please look into this as soon as possible.",
    "I would appreciate a quick response.",
    "Kindly assist me before the deadline.",
    "Please advise on the next steps.",
    "I need this resolved urgently.",
    "Thank you for your attention to this matter.",
    "Can someone please help me?",
    "What should I do now?",
    "Please treat this as urgent.",
    "I'll be grateful for your help.",
    "",
    "",
    "",
]

def _maybe_decorate(sentence: str) -> str:
    """Randomly wraps a base sentence with a tone opener and/or closer."""
    opener_roll = random.random()
    if opener_roll < 0.12:
        opener = random.choice(OPENERS_FORMAL)
    elif opener_roll < 0.24:
        opener = random.choice(OPENERS_POLITE)
    elif opener_roll < 0.32:
        opener = random.choice(OPENERS_FRUSTRATED)
    elif opener_roll < 0.38:
        opener = random.choice(OPENERS_PIDGIN)
    else:
        opener = None

    closer = random.choice(CLOSERS) if random.random() < 0.35 else ""

    parts = []
    if opener:
        # Every opener here is a lead-in clause, so the sentence that
        # follows always gets folded into lowercase (e.g. "Kindly note
        # that there was..." rather than "...that There was...").
        body = sentence[0].lower() + sentence[1:]
        parts.append(opener)
        parts.append(body)
    else:
        parts.append(sentence)
    if closer:
        parts.append(closer)
    return " ".join(p for p in parts if p).strip()

_INFORMAL_SUBS = [
    (" please", " pls"),
    (" because", " cos"),
    (" before", " b4"),
    (" and ", " & "),
]

def _maybe_informalize(sentence: str) -> str:
    """Applies at most one light informal substitution ~18% of the time."""
    if random.random() < 0.18:
        candidates = [pair for pair in _INFORMAL_SUBS if pair[0] in sentence.lower()]
        if candidates:
            old, new = random.choice(candidates)
            # case-insensitive single replacement
            idx = sentence.lower().find(old)
            sentence = sentence[:idx] + new + sentence[idx + len(old):]
    if random.random() < 0.1:
        sentence = sentence.rstrip(".")
    if random.random() < 0.08:
        sentence = sentence[0].lower() + sentence[1:]
    return sentence

# ---------------------------------------------------------------------------
# Per-category sentence skeletons. `{code}`, `{code2}`, `{session}`,
# `{level}`, `{dept}`, `{courseA}`, `{courseB}`, `{amount}` are filled from
# _placeholders(). Skeletons with no placeholders are valid too (short,
# generic complaints/questions).
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, list[str]] = {
    "Missing Result": [
        "My {code} result has not appeared since {session}.",
        "I sat for the {code} exam in {session} but the result is still not showing on the portal.",
        "My result for {code} is missing from my {level} result checker.",
        "The result for {code} from {session} has not been uploaded till now.",
        "I checked my results page and {code} is not there even though I wrote the exam.",
        "My {level} results are incomplete; {code} is missing.",
        "It has been over a month and my {code} result still has not been released.",
        "Why is my {code} result not showing up on the student portal?",
        "I need my {code} result urgently, it is not on my summary page.",
        "My carry-over result for {code} taken in {session} has not reflected.",
        "Result for {code} missing - I wrote the exam but nothing shows on my dashboard.",
        "{code} result is missing from my broadsheet for {session}.",
        "{code} result no dey show for portal since {session}, abeg check am.",
        "My entire {level} first semester results are missing except for two courses.",
        "I have checked several times but my {code} result is not on the portal.",
        "Missing result: {code}, {session}. I have proof of attendance and script submission.",
        "Kindly investigate why my {code} score was never uploaded to the portal.",
        "My {code} grading is complete according to my lecturer, but the portal still shows nothing.",
        "My result summary is incomplete for {level}; {code} in particular is blank.",
        "I resat {code} in {session} and the new result has not been posted.",
        "Result missing for {code}, please check with the exams office.",
        "None of my results for {session} have shown up yet, is there a delay?",
        "My {code} result vanished from the portal after showing briefly last week.",
        "Is there a reason my {code} result is still pending after two months?",
        "I can see results for other courses but {code} is completely absent.",
        "result for {code} still no dey show, e don tey since {session}.",
        "My friends who wrote {code} with me already have their results, mine is still missing.",
        "Please, {code} result missing since {session}, when will it be uploaded?",
    ],
    "Grade Dispute": [
        "I believe my grade for {code} is wrong; I scored higher in the exam than what is showing.",
        "My {code} grade shows a D but I am certain I passed with a B.",
        "There is a mismatch between my continuous assessment score and the final grade for {code}.",
        "I want to appeal my grade in {code}; I believe there was an error in marking.",
        "My {code} script was remarked before but the grade was never updated.",
        "The grade posted for {code} does not match what my lecturer announced in class.",
        "I am requesting a recheck of my {code} exam script.",
        "Something is wrong with my {code} grade, it dropped from what was originally announced.",
        "Please recompute my {code} grade, I don't think the CA score was added correctly.",
        "I scored 68 in {code} continuous assessment but the portal shows an F for the course.",
        "This grade for {code} does not make sense to me, I need it reviewed.",
        "My coursemates and I received different grades for the same {code} exam despite similar performance.",
        "I suspect my {code} grade was mixed up with another student's result.",
        "Grade dispute for {code}: I attended all classes and submitted every assignment, yet I got an E.",
        "How do I formally challenge a grade I believe is incorrect for {code}?",
        "My {code} grade seems too low compared to my classmates who wrote the same exam.",
        "I have evidence from my exam script that my {code} grade should be higher.",
        "Please explain how my {code} grade was calculated, it doesn't add up.",
        "I need a grade appeal form for {code}, I believe the total score was entered wrongly.",
        "My {code} result was downgraded from what was posted on the noticeboard.",
        "This {code} grade no correct at all, I dey sure say I do well for the exam.",
        "I want an official review of my {code} grade before the deadline for appeals.",
        "The class average for {code} was low, but I believe my individual score was still miscalculated.",
        "My lecturer confirmed I passed {code}, but my transcript shows a fail grade.",
        "There seems to be a data entry error affecting my {code} grade.",
        "Please compare my {code} script with the marking scheme, my grade looks off.",
    ],
    "Course Registration": [
        "I am unable to register {code} on the portal, it keeps showing an error message.",
        "The course registration portal will not let me add {code} for {session}.",
        "I can't find {code} in the list of courses available for {level}.",
        "My course registration for {session} is not going through, the submit button doesn't respond.",
        "I need help registering a carryover course, {code}, for {session}.",
        "The registration deadline has passed but I still need to register {code}.",
        "There is a clash between {code} and another course preventing my registration.",
        "Please reopen the portal so I can complete my course registration.",
        "I mistakenly registered the wrong course instead of {code}, please help me correct it.",
        "My total registered units exceed the limit and I can't add {code}.",
        "I have not been able to register any course for {session} due to a portal error.",
        "How do I drop {code} from my registered courses this semester?",
        "My registered courses list is empty even though I completed the registration process for {session}.",
        "Please assist, I cannot generate my course form for {level}.",
        "The system won't let me register {code} because it says I haven't cleared a prerequisite.",
        "I need to swap {courseA} for {courseB} in my course registration.",
        "Registration for {code} keeps timing out whenever I try to submit.",
        "I registered late for {session} and now the portal is blocking new registrations.",
        "pls help, I dey try register {code} but the portal no gree accept am.",
        "My adviser has not approved my course form for {session} yet.",
        "I can't print my course registration slip after submitting for {level}.",
        "The number of units showing on my course form is incorrect for {session}.",
        "I keep getting an 'already registered' error for {code} which I have never taken.",
        "Please advise how to register a deferred course from {session}.",
        "My course registration shows as pending approval for over two weeks now.",
    ],
    "Transcript Request": [
        "I applied for my transcript to be sent to {dept} department but it has not arrived after three weeks.",
        "Please, I need my official transcript processed urgently for a job application.",
        "I paid for my transcript in {session} but have not received any update.",
        "How long does transcript processing normally take?",
        "My transcript request submitted since {session} is still pending.",
        "I need my transcript sent electronically to a university abroad.",
        "There is an error on my transcript; it does not include my {code} result.",
        "Please provide an update on my transcript request reference number.",
        "I need a hard copy of my transcript for my NYSC registration.",
        "My transcript was returned undelivered, can it be resent?",
        "I completed the transcript request form but never received a confirmation email.",
        "Can I request my transcript online, or must I come in person?",
        "My transcript is missing a page covering my {level} results.",
        "I paid the transcript fee of {amount} but the status still shows unprocessed.",
        "Please expedite my transcript request, I have an admission deadline approaching.",
        "I need multiple copies of my transcript sent to different institutions.",
        "My name on the transcript is spelled incorrectly, please correct and reissue it.",
        "Abeg, how far with my transcript, I don dey wait since {session}.",
        "I submitted my transcript request but haven't received the tracking details.",
        "What is the current status of my transcript request?",
        "My transcript request was rejected, but no reason was given.",
        "Please confirm if my transcript has been dispatched yet.",
        "I need an evaluation-ready transcript for a scholarship application.",
        "The transcript office asked for a re-submission but did not explain why.",
    ],
    "Academic Clearance": [
        "I need clearance from my department before I can graduate.",
        "My academic clearance form is missing a signature from the {dept} department.",
        "Please assist with my final year clearance, the library section is not signing off.",
        "I cannot complete my clearance because of an outstanding issue with {code}.",
        "My clearance for graduation has been delayed for weeks now.",
        "What documents do I need for academic clearance?",
        "I have completed all clearance steps except the bursary section.",
        "My department is asking for a document I already submitted for clearance.",
        "Please clarify the clearance process for {level} students.",
        "I need clearance to change from {courseA} to {courseB}.",
        "My clearance form was rejected without an explanation.",
        "How do I get clearance from the hostel office as part of my final clearance?",
        "I have an outstanding library book blocking my academic clearance.",
        "Please expedite my clearance, my convocation is in two weeks.",
        "My clearance officer has not been available to sign my forms.",
        "I need to know which offices to visit for graduation clearance.",
        "My clearance is stuck because of a missing signature from my course adviser.",
        "abeg who go help me sign my clearance form, I don waka reach three offices.",
        "I completed clearance last {session} but it was not recorded on the system.",
        "Please confirm if my clearance has been approved by the dean's office.",
        "My clearance status still shows incomplete despite submitting all requirements.",
        "I need clearance for change of department from {dept}.",
    ],
    "Examination Issue": [
        "I was denied entry into the {code} exam hall because my name was not on the attendance list.",
        "There is a clash between {code} and another exam scheduled on the same day.",
        "I missed my {code} exam due to illness and need to know how to apply for a resit.",
        "My exam script for {code} seems to have been misplaced.",
        "I was accused of malpractice during the {code} exam and I want to appeal the decision.",
        "The invigilator would not allow me extra time despite my medical condition.",
        "My exam timetable shows two papers scheduled at the same time slot.",
        "I need an update on the {code} exam venue, it was not communicated.",
        "Please reschedule my {code} exam, I had a medical emergency on the exam date.",
        "My exam card was not generated for {code}, so I could not sit the paper.",
        "The {code} exam started late but we were not given extra time to compensate.",
        "I submitted my {code} script but there is no record of it on file.",
        "What is the procedure to request a supplementary exam for {code}?",
        "My seat number for the {code} exam was not on the seating plan.",
        "There was a power outage during the {code} exam and no extra time was given.",
        "I need clarification on the exam malpractice allegation raised against me for {code}.",
        "Please confirm if the {code} exam has been rescheduled due to the strike.",
        "My {code} exam paper had missing pages when I received it.",
        "I was not informed about a change in {code} exam venue and I missed the paper.",
        "Can I get a copy of the {code} exam question paper for review?",
        "e be like say dem misplace my {code} script, I don submit am since.",
        "The exam supervisor refused to let me leave for a bathroom break during {code}.",
        "I need an official letter explaining why my {code} exam was cancelled.",
    ],
    "School Fees Issue": [
        "I paid my school fees but it is not reflecting on the portal.",
        "My receipt shows successful payment but my portal still shows outstanding fees.",
        "I was charged the wrong amount for {session} school fees.",
        "Please help, my fee payment of {amount} has not been acknowledged.",
        "I need a refund for an accidental duplicate fee payment.",
        "My scholarship deduction was not applied to my fees for {session}.",
        "The installment payment plan is not showing correctly on my account.",
        "I paid through the bank but the portal still requests payment for {session}.",
        "My fee payment was reversed by my bank but the portal still shows it as paid.",
        "Please generate a new invoice, the current one shows an incorrect amount.",
        "I have not received a receipt for my fee payment made last week.",
        "My acceptance fee payment is not reflecting even after a week.",
        "There is a discrepancy of {amount} between what I paid and what is recorded.",
        "I need to know if late payment attracts a penalty for {session}.",
        "Please confirm my fee balance for {level}, the figure shown seems too high.",
        "My fee payment reference number is not being recognized by the portal.",
        "I paid my fees in full but I am still being blocked from registering courses.",
        "abeg, I don pay my school fees since last week but e no dey show for portal.",
        "Can I get an official statement of my fee payment history?",
        "My hostel fee and tuition fee are showing as one combined amount, please separate them.",
        "I was mistakenly charged fees for a department I am not part of.",
        "Please advise on how to resolve a failed fee transaction of {amount}.",
    ],
    "Portal/System Issue": [
        "I cannot log into the student portal, it keeps showing an invalid credentials error.",
        "The student portal has been down since yesterday.",
        "I forgot my password and the reset link on the portal is not working.",
        "Every time I try to upload my document, the portal shows a server error.",
        "The portal page keeps freezing whenever I try to view my dashboard.",
        "I'm getting a 500 error whenever I try to access my profile page.",
        "The portal logs me out automatically after a few seconds.",
        "My profile picture upload keeps failing on the portal.",
        "The portal is extremely slow and times out before pages load.",
        "I can't access the portal from my phone, only from a computer.",
        "The portal shows a blank page after I log in.",
        "My two-factor authentication code for the portal never arrives.",
        "The portal keeps showing an outdated version of my information.",
        "I can't download any documents from the student portal.",
        "The portal's notification system is not sending me any updates.",
        "Please fix the portal, the search feature is not returning any results.",
        "portal don hang since morning, I no fit do anything on my dashboard.",
        "The mobile app version of the portal crashes every time I open it.",
        "I keep getting logged into someone else's account when I sign in.",
        "The portal will not accept my correct login details no matter how many times I try.",
        "There seems to be a bug causing duplicate entries on my student dashboard.",
        "The portal's calendar feature is not showing the correct semester dates.",
    ],
    "Admission Issue": [
        "My admission status still shows pending after screening.",
        "I have not received my admission letter despite meeting the cut-off mark.",
        "There is a discrepancy between my JAMB course choice and my admitted course.",
        "I want to change my course of admission from {courseA} to {courseB}.",
        "My post-UTME result has not been used to process my admission.",
        "I was offered admission but the portal will not let me accept it.",
        "My name is missing from the admission list even though I scored above the cut-off.",
        "Please confirm if my documents for admission screening were received.",
        "I need to know the status of my change-of-course request after admission.",
        "My admission letter shows the wrong department.",
        "The JAMB CAPS platform shows my admission but the school portal does not reflect it.",
        "I am yet to be given a matriculation number after admission.",
        "Please advise on the next steps after provisional admission for {session}.",
        "My admission was withdrawn without any explanation.",
        "I missed the screening exercise due to a family emergency, can I be rescheduled?",
        "There seems to be a delay in processing admissions for {dept} this session.",
        "abeg check my admission status, e never change since I submit my documents.",
        "I need clarification on the supplementary admission list for {session}.",
        "My O'level result upload for admission verification keeps failing.",
        "Can transfer students still apply for admission into {dept} this session?",
        "I have not been able to print my admission letter from the portal.",
    ],
    "Certificate Collection": [
        "I graduated in {session} but have not been able to collect my certificate.",
        "My certificate has an error in the spelling of my name.",
        "How do I schedule an appointment to collect my degree certificate?",
        "My employer needs to verify my certificate, who should I contact?",
        "I lost my original certificate and need a replacement or verification letter.",
        "My certificate has not been ready months after my convocation.",
        "Please confirm if my certificate is ready for collection.",
        "I need my certificate collected by proxy since I am out of the country.",
        "My certificate shows the wrong graduation date.",
        "What is the process for certificate collection after convocation?",
        "I paid the certificate processing fee but have not received a collection date.",
        "My certificate was misplaced by the records office, what do I do?",
        "Can I request a statement of result while waiting for my certificate?",
        "I need an authentication letter for my certificate for an international application.",
        "My degree class on the certificate does not match my final CGPA.",
        "abeg my certificate never ready since {session}, wetin dey happen?",
        "Please advise on the fastest way to obtain a duplicate certificate.",
        "I need to know if certificates can be couriered to a different city.",
        "My name on the certificate does not match my admission records.",
        "How long after convocation does it typically take to collect a certificate?",
    ],
    "Student Welfare": [
        "I have not been allocated a hostel room despite applying early.",
        "My hostel room has had no water supply for over a week.",
        "I would like to report a case of harassment from another student.",
        "I need counseling support due to personal difficulties affecting my studies.",
        "The health center refused to attend to me during an emergency.",
        "I am facing financial hardship and need information on student support funds.",
        "Please look into the security situation around the female hostel.",
        "My hostel roommate situation has become unsafe and needs urgent attention.",
        "I need information about disability accommodations for my exams.",
        "The food served at the cafeteria has caused several students to fall ill.",
        "I would like to report bullying from a coursemate.",
        "Please assist, I am struggling financially and considering deferring my studies.",
        "The lighting around the hostel area is poor and feels unsafe at night.",
        "I need to speak with a counselor about stress affecting my academics.",
        "There has been no electricity in my hostel block for several days.",
        "I want to report an incident of sexual harassment by a staff member.",
        "Please help, I need emergency financial assistance for medical treatment.",
        "abeg the hostel toilets don spoil since last month, nobody don fix am.",
        "I need support accessing mental health resources on campus.",
        "My scholarship stipend has not been paid and I am struggling to survive on campus.",
        "Is there a support program for students with physical disabilities?",
        "I would like to report unsafe conditions in the male hostel block.",
        "Please provide information on how to access the student welfare fund.",
    ],
    "Other": [
        "I lost my student ID card and need a replacement.",
        "There is a spelling error in my name on my student record.",
        "How can I get in touch with my course adviser?",
        "I would like to request a recommendation letter from my department.",
        "What are the school's resumption dates for next session?",
        "I have a general suggestion about improving the student portal.",
        "Please, who do I contact regarding a query not related to academics?",
        "I need to update my phone number and address on my student record.",
        "Can I get information about extracurricular clubs on campus?",
        "I would like feedback on how to file a general complaint.",
        "My guardian's contact information needs to be updated in school records.",
        "How do I request an official letter confirming my student status?",
        "I need to know the procedure for a name change on my student file.",
        "Please advise who handles general enquiries not covered by other departments.",
        "I want to give feedback about the quality of teaching in my department.",
        "abeg I just wan know when next semester go start.",
        "I need a bonafide student status letter for a visa application.",
        "Can someone direct me to the right office for a general enquiry?",
        "I would like to nominate a lecturer for a teaching excellence award.",
        "My question doesn't fit any specific category, please redirect me.",
        "I need information about internship opportunities through the school.",
        "Please let me know the process for reporting lost property on campus.",
    ],
}


def _generate_category(category: str, count: int, seen: set[str]) -> list[tuple[str, str]]:
    """Returns a list of (text, template_id) pairs. template_id identifies
    which sentence skeleton produced the row (e.g. "Missing Result::4") --
    this is written to the CSV so train_classifier.py can split train/test
    by template group rather than by row, preventing the same skeleton
    (with only a course code/session swapped) from appearing on both sides
    of the split. See train_classifier.py's grouped-split rationale."""
    templates = TEMPLATES[category]
    results: list[tuple[str, str]] = []
    attempts = 0
    max_attempts = count * 40

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        idx = random.randrange(len(templates))
        template = templates[idx]
        filled = template.format(**_placeholders()) if "{" in template else template
        text = _maybe_decorate(filled)
        text = _maybe_informalize(text)
        text = " ".join(text.split())  # collapse any doubled whitespace
        if text not in seen:
            seen.add(text)
            results.append((text, f"{category}::{idx}"))

    if len(results) < count:
        raise RuntimeError(
            f"Could not generate {count} unique examples for '{category}' "
            f"after {max_attempts} attempts (got {len(results)})."
        )
    return results


def main() -> None:
    seen: set[str] = set()
    rows: list[tuple[str, str, str]] = []

    for category in CATEGORIES:
        examples = _generate_category(category, EXAMPLES_PER_CATEGORY, seen)
        rows.extend((text, category, template_id) for text, template_id in examples)

    random.shuffle(rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "category", "template_id"])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} examples to {OUTPUT_PATH}")
    counts: dict[str, int] = {}
    for _, cat, _tid in rows:
        counts[cat] = counts.get(cat, 0) + 1
    for cat in CATEGORIES:
        n_templates = len(TEMPLATES[cat])
        print(f"  {cat:24s} {counts.get(cat, 0):4d} examples  ({n_templates} templates)")


if __name__ == "__main__":
    main()
