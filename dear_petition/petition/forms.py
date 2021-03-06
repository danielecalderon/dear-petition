import io
import os

from django import forms
from django.conf import settings

from dear_petition.petition.models import CIPRSRecord, Contact, Batch
from dear_petition.petition.writer import Writer
from dear_petition.petition.data_dict import map_data


class UploadFileForm(forms.Form):
    files = forms.FileField(widget=forms.ClearableFileInput(attrs={"multiple": True}))

    def save(self):
        batch = Batch.objects.create()
        for file_ in self.files.getlist("files"):
            record = CIPRSRecord()
            if settings.CIPRS_SAVE_PDF:
                record.report_pdf = file_
            record.data = record.parse_report(file_)
            if "error" in record.data:
                raise forms.ValidationError(record.data["error"])
            if "Defendant" in record.data and "Name" in record.data["Defendant"]:
                record.label = record.data["Defendant"]["Name"]
            record.save()
            batch.records.add(record)
        return batch


class GeneratePetitionForm(forms.Form):

    attorney = forms.ModelChoiceField(
        queryset=Contact.objects.filter(category="attorney"), required=False
    )
    agency1 = forms.ModelChoiceField(
        queryset=Contact.objects.filter(category="agency"),
        label="Agency #1",
        required=False,
    )
    agency2 = forms.ModelChoiceField(
        queryset=Contact.objects.filter(category="agency"),
        label="Agency #2",
        required=False,
    )
    as_attachment = forms.BooleanField(
        required=False, help_text="Download PDF as an attachment (off by default)"
    )

    def __init__(self, *args, **kwargs):
        self.batch = kwargs.pop("batch")
        super().__init__(*args, **kwargs)

    def clean_attorney(self):
        data = self.cleaned_data["attorney"]
        if data:
            return {
                "NameAtty": data.name,
                "StAddrAtty": data.address1,
                "MailAddrAtty": data.address2,
                "CityAtty": data.city,
                "StateAtty": data.state,
                "ZipCodeAtty": data.zipcode,
            }

    def clean_agency1(self):
        data = self.cleaned_data["agency1"]
        if data:
            return {
                "NameAgency1": data.name,
                "AddrAgency1": data.address1,
                "MailAgency1": data.address2,
                "CityAgency1": data.city,
                "StateAgency1": data.state,
                "ZipAgency1": data.zipcode,
            }

    def clean_agency2(self):
        data = self.cleaned_data["agency2"]
        if data:
            return {
                "NameAgency2": data.name,
                "AddrAgency2": data.address1,
                "MailAgency2": data.address2,
                "CityAgency2": data.city,
                "StateAgency2": data.state,
                "ZipAgency2": data.zipcode,
            }

    def save(self):
        output = io.BytesIO()
        template_path = os.path.join(
            settings.APPS_DIR, "static", "templates", "petition-template.pdf"
        )
        form_data = self.cleaned_data.copy()
        del form_data["as_attachment"]
        petition = Writer(form_data, self.batch, template_path, output)
        petition.get_annotations()
        petition.write()
        output.seek(0)
        return output
