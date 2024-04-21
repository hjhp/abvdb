from django.shortcuts import render
from django.views import generic
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.contrib.auth.decorators import login_required

import csv
import json

from .models import Abv
from .forms import AbvSubmitSingle, AbvSubmitFile

# Create your views here.

def index(request):
    """Homepage"""
    context = {
    }
    return render(request, "index.html", context = context)

@login_required
def submit(request):
    """A primitive form"""
    # POST
    if request.method == "POST":
        if request.user.is_authenticated:
            if "submit_single" in request.POST:
                abv_form = AbvSubmitSingle(request.POST)
                if abv_form.is_valid():
                    intermediary_form = abv_form.save(commit=False) # commit=False to restore the submittor_ip field, which is excluded from the HTML form.
                    intermediary_form.submittor_ip = request.META['REMOTE_ADDR']
                    intermediary_form.user_id = request.user.id # https://forum.djangoproject.com/t/automatically-get-user-id-to-assignate-to-form-when-submitting/5333/8 which gives the basic outline; https://stackoverflow.com/a/3855829
                    intermediary_form.save() 
                    # todo: Implement django.contrib messages to display a "thank you".
                    return HttpResponse(r"<p>Thank you.</p>")
                else:
                    return HttpResponse("<p>Error(s).</p>")
            elif "submit_file" in request.POST:
                abv_form = AbvSubmitFile(request.POST, request.FILES)
                if abv_form.is_valid():
                    # All the "intermediary" steps applicable to submit_single do not apply here, because AbvSubmitFile is not a ModelForm: it is just a Form. Therefore the request will have to be broken down and the model updated manually.
                    # Set constants
                    submittor_ip = request.META['REMOTE_ADDR']
                    user_id = request.user.id
                    csv_file = request.FILES["file"]
                    try:
                        data = csv.DictReader(csv_file.read().decode("utf-8").splitlines())
                    except:
                        return HttpResponse(f"<p>Error(s) parsing file.</p><pre>{abv_form.errors.as_data()}</pre>")
                    score_sheet = []
                    for item in data:
                        try:
                            record = Abv(
                                lwin11 = item["lwin11"],
                                abv = item["abv"],
                                submittor_ip = submittor_ip,
                                user_id = user_id,
                            )
                            record.full_clean() # Run validation on each row based on the rules defined in models.py.
                            record.save()
                            item["success"] = 1
                            score_sheet.append(item)
                        except ValidationError as e:
                            item["success"] = 0
                            item["reason"] = str(e) # Stringify here else can't use json.dumps later for pretty-printing.
                            score_sheet.append(item)
                            continue
                        except KeyError as e:
                            return HttpResponse(f"<p>Required field(s) not found: <pre>{e}</pre></p>")
                    return HttpResponse(f"<pre>{json.dumps(score_sheet, indent=4, sort_keys=False)}</pre>")
                    # return HttpResponse(f"<p>{score_sheet}</p>")
                else:
                    return HttpResponse(f"<p>Error(s) in form.</p><pre>{abv_form.errors.as_data()}</pre>")
            else:
                return HttpResponse(f"<p>Dead end. Which form button did you submit?</p><pre>{abv_form.errors.as_data()}</pre>")
    # GET
    else:
        form_single = AbvSubmitSingle()
        form_file = AbvSubmitFile()
        context = {
            "form_single": form_single,
            "form_file": form_file,
        }
        return render(request, "submit.html", context = context)

def data_raw_csv(request):
    """CSV response of raw data."""
    query_results = Abv.objects.all()
    response = HttpResponse(
        content_type = "text/csv",
        headers = {
            "Content-Disposition": 'attachment; filename="abvdb.csv"'
        },
    )
    writer = csv.writer(response)
    writer.writerow(["lwin11", "abv", "date_created"])
    write_me = []
    for item in query_results:
        write_me.append([
            item.lwin11,
            item.abv,
            item.date_created,
        ])
    writer.writerows(write_me)
    return response

def data_latest_per_user_csv(request):
    """CSV response of latest data per user.
    Window function taken from https://stackoverflow.com/a/2411703.
    """
    query_results = Abv.objects.raw("SELECT x.id, x.user_id, x.lwin11, x.abv FROM (SELECT id, user_id, lwin11, abv, row_number() OVER (PARTITION BY lwin11, user_id ORDER BY date_created DESC) AS row_number FROM abv_abv) AS x WHERE row_number=1;") # https://docs.djangoproject.com/en/5.0/topics/db/sql/
    response = HttpResponse(
        content_type = "text/csv",
        headers = {
            "Content-Disposition": 'attachment; filename="abvdb_latest-per-user.csv"'
        },
    )
    writer = csv.writer(response)
    writer.writerow([
        "lwin11",
        "abv",
        "date_created",
        "user_id",
    ])
    write_me = []
    for item in query_results:
        write_me.append([
            item.lwin11,
            item.abv,
            item.date_created,
            item.user_id,
        ])
    writer.writerows(write_me)
    return response

def data_majority_vote_csv(request):
    """CSV response of the most-users-submitted ABV value per LWIN11.
    Only counts distinct submittors (that is, it is not possible for a submittor to spam-upvote an ABV-LWIN11 pair by submitting the same data multiple times.)

    However, it takes into account all pairs ever submitted by a submittor, rather than taking only the ABV from their most recent submission.
    This is arguably a controversial decision — what if the submittor made an erroneous submission and immediately did a subsequent upload to correct their mistake? — but consider a hypothetical old wine that has variation in the ABV declaration between batches (bearing in mind standardisation in wine is a relatively recent issue, with even France's AOC system under 100 years old as of 2024); one submittor happens to own two batches of the same wine and each batch declares a different ABV: should such a quirk not be accounted for?

    Regarding the possibility for an erroneous upload, it would surely be better protocol to have the submittor contact the administrator to request deletion of the entire upload session, rather than implementing undeclared/automatic behaviour such as each subsequent upload overwriting the previous.
    There is, of course, an assumption of good-faith submittors here, but this is always the case with crowd-sourcing and some level of moderation — whether manually approving sign-ups or regularly identifying and banning malicious accounts — will always be needed.

    One hopes that, with even weak adherence to the DRY principle, erroneous good-faith uploads should be rare: it is expected that contributions to this database will largely be made by pulling data from existing sources (e.g. a warehouse inventory report).
    This database is simply intended to be an open aggregator of the various commercially-motivated databases already in existence (e.g. LivEx, Wine Owners, London City Bond…).

    If multiple ABV-LWIN11 pairs have been submitted by the same number of submittors, both pairs will be displayed, because there is no reasonably fair way to decide in such a case.
    (From a commercial standpoint, one would say that the higher ABV should be chosen, because at least in the UK, ABV can influence Duty due and it is almost always safer to err on the side of giving more money to the government — but this is not a commercially-minded project.)
    """
    query_results = Abv.objects.raw("SELECT x.id, MAX(x.number_of_users_voted) AS number_of_users_voted, x.lwin11, x.abv FROM (SELECT id, COUNT(DISTINCT user_id) AS number_of_users_voted, lwin11, abv FROM abv_abv GROUP BY lwin11, abv ORDER BY lwin11 ASC) AS x GROUP BY lwin11;") # https://docs.djangoproject.com/en/5.0/topics/db/sql/
    response = HttpResponse(
        content_type = "text/csv",
        headers = {
            "Content-Disposition": 'attachment; filename="abvdb_majority-vote.csv"'
        },
    )
    writer = csv.writer(response)
    writer.writerow([
        "lwin11",
        "abv",
        "number_of_users_voted",
    ])
    write_me = []
    for item in query_results:
        write_me.append([
            item.lwin11,
            item.abv,
            item.number_of_users_voted,
        ])
    writer.writerows(write_me)
    return response

def data_raw_html(request):
    """HTML table of raw data. Considered lower-priority than the csv variant."""
    query_results = Abv.objects.values("lwin11", "abv", "date_created").order_by("lwin11", "date_created") # We do not use Abv.objects.all() here because the dynamic nature of template/data.html only works with the dict_keys generated by Abv.objects.values(). That is, instead of the view returning a context with all the data and the HTML template controlling what gets displayed, we have put the onus of field selection onto the view, and created an HTML template that simply displays everything it receives.
    context = {
        "query_results": query_results,
    }
    return render(request, "data_table.html", context = context)

def data_voted_html(request):
    # Todo: make csv variant af this. But the syntax for accessing data obtained by Model.objects.values("field 1") is different to that for Model.objects.all(); some study needed.
    """A consolidated view with unique LWIN11-and-ABV pairs only, plus an extra count column for how many times a pair has been submitted, which may serve as a crowd-sourced vote of confidence as to its accuracy."""
    query_results = Abv.objects.values("lwin11", "abv").annotate(voted=Count("abv")).order_by("lwin11") # SQL: SELECT lwin11, abv, COUNT(abv) FROM abv_abv GROUP BY lwin11, abv;
    context = {
        "query_results": query_results,
    }
    return render(request, "data_table.html", context = context)
