# automation/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    PowerOfAttorneySerializer, TenderSecuringDeclarationSerializer,
    LitigationHistorySerializer, CoverLetterSerializer
)
from .models import (
    PowerOfAttorney, TenderSecuringDeclaration,
    LitigationHistory, CoverLetter
)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from django.http import HttpResponse
from io import BytesIO
import textwrap
import datetime

class PowerOfAttorneyView(APIView):
    def post(self, request):
        serializer = PowerOfAttorneySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, id=None):
        if id:
            obj = PowerOfAttorney.objects.get(id=id)
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            margin = inch
            line_height = 0.2 * inch
            font_size = 12
            p.setFont("Helvetica-Bold", font_size)
            y = height - margin
            p.drawCentredString(width / 2, y, "STANDARD POWER OF ATTORNEY")
            y -= line_height * 2
            p.setFont("Helvetica", font_size)
            text = "TO ALL IT MAY CONCERN"
            p.drawCentredString(width / 2, y, text)
            y -= line_height * 2
            day_suffix = "th" if obj.date.day > 3 and obj.date.day < 21 else {1: "st", 2: "nd", 3: "rd"}.get(obj.date.day % 10, "th")
            date_str = f"{obj.date.day}{day_suffix}, {obj.date.strftime('%B')} {obj.date.year}"
            text = f"THAT BY THIS POWER OF ATTORNEY given on the {date_str},"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = f"WE the undersigned {obj.company_name.upper()} of {obj.address}, P.O. Box {obj.po_box}, Temeke, Dar es Salaam, Tanzania, by virtue of authority conferred to us by the Board Resolution No {obj.board_resolution_no} of {obj.board_resolution_year}, do hereby ordain, nominate authorize, empower and appoint {obj.attorney_name.upper()} of {obj.attorney_address}, to be our true lawful Attorney and Agent, with full power and authority, for us and in our names, and for our accounts and benefits, to do any, or all of the following acts, in the execution of tender No. {obj.tender_no} for {obj.tender_description.upper()} that is to say;"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text_lines = [
                "To",
                "act",
                "for",
                "the",
                "company and",
                "do",
                "any other",
                "thing",
                "or",
                "things",
                "incidental",
                "for"
            ]
            for text in text_lines:
                p.drawString(margin, y, text)
                y -= line_height
            text = f"{obj.tender_no} for {obj.tender_description.upper()} for the TAA- ARUSHA INTERNATIONAL CONFERENCE CENTRE;"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = "AND provided always that this Power of Attorney shall not revoke or in any manner affect any future power of attorney given to any other person or persons for such other power or powers shall remain and be of the same force and affect as if this deed has not been executed."
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = "AND we hereby undertake to ratify everything, which our Attorney or any substitute or substitutes or agent or agents appointed by him under this power on his behalf herein before contained shall do or purport to do in virtue of this Power of Attorney."
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = f"SEALED with the common seal of the said {obj.company_name.upper()} and delivered in the presence of us this {date_str}."
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = f"IN WITNESS whereof we have signed this deed on this {date_str} at Dar es Salaam for and on behalf of {obj.company_name.upper()}"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = f"SEALED and DELIVERED by the Common Seal of {obj.company_name.upper()} This {date_str}"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height * 2
            p.drawString(margin, y, "DONOR")
            y -= line_height * 2
            p.drawString(margin, y, "BEFORE ME:")
            y -= line_height
            p.drawString(margin, y, "COMMISSIONER FOR OATHS")
            p.showPage()
            y = height - margin
            p.setFont("Helvetica-Bold", font_size)
            p.drawCentredString(width / 2, y, "ACKNOWLEDGEMENT")
            y -= line_height * 2
            p.setFont("Helvetica", font_size)
            text = f"I {obj.attorney_name.upper()} doth hereby acknowledge and accept to be Attorney of the said {obj.company_name.upper()} under the terms and conditions contained in this POWER OF ATTORNEY and I promise to perform and discharge my duties as the lawfully appointed Attorney faithfully and honestly."
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height * 2
            text = f"SIGNED AND DELIVERED by the said {obj.attorney_name.upper()} The latter known to me personally This {date_str},"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height * 2
            p.drawString(margin, y, "DONEE")
            y -= line_height * 2
            p.drawString(margin, y, "BEFORE ME")
            y -= line_height
            p.drawString(margin, y, "COMMISSIONER FOR OATHS")
            p.save()
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="power_of_attorney.pdf"'
            return response
        else:
            queryset = PowerOfAttorney.objects.all()
            serializer = PowerOfAttorneySerializer(queryset, many=True)
            return Response(serializer.data)

class TenderSecuringDeclarationView(APIView):
    def post(self, request):
        serializer = TenderSecuringDeclarationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, id=None):
        if id:
            obj = TenderSecuringDeclaration.objects.get(id=id)
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            margin = inch
            line_height = 0.2 * inch
            font_size = 12
            p.setFont("Helvetica-Bold", font_size)
            y = height - margin
            p.drawCentredString(width / 2, y, "Form of Tender Securing Declaration")
            y -= line_height
            p.setFont("Helvetica", 10)
            p.drawString(margin, y, f"Date: {obj.date}")
            y -= line_height
            p.drawString(margin, y, f"Tender No.: {obj.tender_no}")
            y -= line_height
            p.drawString(margin, y, f"To: {obj.procuring_entity.upper()}")
            y -= line_height * 2
            p.setFont("Helvetica", font_size)
            text = "We, the undersigned, declare that:"
            p.drawString(margin, y, text)
            y -= line_height
            text = "We understand that, according to your conditions, tenders must be supported by a Tender Securing Declaration."
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            text = "We accept that we will automatically be suspended from being eligible for tendering in any contract with the PE for the period of time as determined by the Authority if we are in breach of our obligation(s) under the conditions, because we:"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            text = "(a) have withdrawn or modified our Tender during the period of tender validity specified in the Form of Tender; or"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            text = "(b) having been notified of the acceptance of our Tender by the PE during the period of tender validity, (i) failure to sign the contract if required by PE to do so or (ii) fail or refuse to furnish the Performance Security or to comply with any other condition precedent to signing the contract specified in the tendering documents."
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            text = "We understand this Tender Securing Declaration shall expire if we are not the successful Tenderer, upon the earlier of (i) our receipt of your notification to us of the name of the successful Tenderer; or (ii) twenty-eight (28) days after the expiration of our Tender."
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = f"Signed in the capacity of {obj.signer_capacity}"
            p.drawString(margin, y, text)
            y -= line_height
            text = f"Name: {obj.signer_name}"
            p.drawString(margin, y, text)
            y -= line_height * 2
            text = f"Duly authorized to sign the tender for and on behalf of: {obj.procuring_entity}"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height * 2
            text = "[Note: In case of a Joint Venture, the Tender Securing Declaration must be in the name of all partners to the Joint Venture that submits the tender.]"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            p.save()
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="tender_securing_declaration.pdf"'
            return response
        else:
            queryset = TenderSecuringDeclaration.objects.all()
            serializer = TenderSecuringDeclarationSerializer(queryset, many=True)
            return Response(serializer.data)

class LitigationHistoryView(APIView):
    def post(self, request):
        serializer = LitigationHistorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, id=None):
        if id:
            obj = LitigationHistory.objects.get(id=id)
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            margin = inch
            line_height = 0.2 * inch
            font_size = 12
            p.setFont("Helvetica-Bold", font_size)
            y = height - margin
            p.drawCentredString(width / 2, y, "STATEMENT AS TO ABSENCE OF LITIGATION RECORD")
            y -= line_height * 2
            p.setFont("Helvetica", font_size)
            text = f"We, {obj.company_name.upper()} of {obj.address} and with P.O. Box {obj.po_box} Dar es Salaam, DO HEREBY declare and state as follows;"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = "1. that there are neither legal, governmental or regulatory actions, suits or proceedings pending to the Company’s knowledge nor any legal, governmental or regulatory investigations, to which the Company or a its Subsidiary is a party or to which any property of the Company or any of its Subsidiaries is the subject that, individually or in the aggregate, if determined adversely to the Company or any of its Subsidiaries, would reasonably be expected to have a Material Adverse Effect or materially and adversely affect the ability of the Company to perform any of its obligations under the Tender {obj.tender_description.upper()}"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = "2. Further that the company has never been a Defendant in any legal proceeding."
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            day_suffix = "th" if obj.date.day > 3 and obj.date.day < 21 else {1: "st", 2: "nd", 3: "rd"}.get(obj.date.day % 10, "th")
            date_str = f"{obj.date.day}{day_suffix} day of {obj.date.strftime('%B')} {obj.date.year}"
            text = f"IN WITNESS whereof we have signed this Statement on proof of no Litigation on this {date_str} at Dar es Salaam for and on behalf of {obj.company_name.upper()}DONOR"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = "SEALED and DELIVERED by the Common Seal of {obj.company_name.upper()}        ………………………"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            text = f"This {obj.date.day}{day_suffix} {obj.date.strftime('%B')} {obj.date.year}"
            p.drawString(margin, y, text)
            y -= line_height * 2
            p.drawString(margin, y, "BEFORE ME:")
            y -= line_height
            p.drawString(margin, y, "COMMISSIONER FOR OATHS")
            p.save()
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="litigation_history.pdf"'
            return response
        else:
            queryset = LitigationHistory.objects.all()
            serializer = LitigationHistorySerializer(queryset, many=True)
            return Response(serializer.data)

class CoverLetterView(APIView):
    def post(self, request):
        serializer = CoverLetterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, id=None):
        if id:
            obj = CoverLetter.objects.get(id=id)
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            margin = inch
            line_height = 0.2 * inch
            font_size = 12
            p.setFont("Helvetica-Bold", font_size)
            y = height - margin
            # Page 1
            # Assume no logo, as no image
            day_suffix = "th" if obj.date.day > 3 and obj.date.day < 21 else {1: "st", 2: "nd", 3: "rd"}.get(obj.date.day % 10, "th")
            date_str = f"{obj.date.day}{day_suffix} {obj.date.strftime('%B')} {obj.date.year}"
            p.drawString(margin, y, date_str)
            y -= line_height * 2
            p.drawString(margin, y, "To:")
            y -= line_height
            text = f"{obj.recipient_title},"
            p.drawString(margin, y, text)
            y -= line_height
            text = obj.recipient_name
            p.drawString(margin, y, text)
            y -= line_height
            lines = textwrap.wrap(obj.recipient_address, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height * 2
            text = f"Sub: {obj.reference_no}"
            p.drawString(margin, y, text)
            y -= line_height * 2
            p.drawString(margin, y, "Dear Madam/Sir,")
            y -= line_height * 2
            lines = textwrap.wrap(obj.company_description, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = "We refer to the above request for expression of interest and have developed our proposal after getting a comprehensive understanding of your organization’s requirements under the Category – Non-consultancy services for the Provision of Air/ Ticketing services as under."
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            p.setFont("Helvetica-Bold", font_size)
            p.drawString(margin, y, "Company Documents:")
            y -= line_height
            p.setFont("Helvetica", font_size)
            text = "All Official documents including the below are attached herewith;"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            attached_docs = obj.attached_docs_list.split('\n') if '\n' in obj.attached_docs_list else obj.attached_docs_list.split(',')
            for i, doc in enumerate(attached_docs, 1):
                text = f"{i}. {doc.strip()}"
                p.drawString(margin + 0.5*inch, y, text)
                y -= line_height
            if y < margin:
                p.showPage()
                y = height - margin
            # Page 2
            y -= line_height
            p.setFont("Helvetica-Bold", font_size)
            p.drawString(margin, y, "Compliance Certificates:")
            y -= line_height
            p.setFont("Helvetica", font_size)
            lines = textwrap.wrap(obj.compliance_certs, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            p.setFont("Helvetica-Bold", font_size)
            p.drawString(margin, y, "Agency Dealership:")
            y -= line_height
            p.setFont("Helvetica", font_size)
            lines = textwrap.wrap(obj.agency_dealership, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            p.setFont("Helvetica-Bold", font_size)
            p.drawString(margin, y, "Lease Agreement:")
            y -= line_height
            p.setFont("Helvetica", font_size)
            lines = textwrap.wrap(obj.lease_agreement, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            p.setFont("Helvetica-Bold", font_size)
            p.drawString(margin, y, "Certified declaration on Litigation information:")
            y -= line_height
            p.setFont("Helvetica", font_size)
            lines = textwrap.wrap(obj.litigation_decl, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            p.setFont("Helvetica-Bold", font_size)
            p.drawString(margin, y, "Similar performance information")
            y -= line_height
            p.setFont("Helvetica", font_size)
            lines = textwrap.wrap(obj.similar_performance, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            p.setFont("Helvetica-Bold", font_size)
            p.drawString(margin, y, "Financial Information")
            y -= line_height
            p.setFont("Helvetica", font_size)
            lines = textwrap.wrap(obj.financial_info, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            p.setFont("Helvetica-Bold", font_size)
            p.drawString(margin, y, "Physical Address & Contact")
            y -= line_height
            p.setFont("Helvetica", font_size)
            lines = textwrap.wrap(obj.physical_address, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = "Our contact details are detailed below;"
            p.drawString(margin, y, text)
            y -= line_height
            # Draw table for business details
            table_data = [
                ("Business Name:", "FLY TODAY TRAVELS COMPANY LIMITED"),
                ("Location:", "KIJITONYAMA"),
                ("Building:", "KAJENGA ROAD"),
                ("Postal Address:", "P. O. Box 24050 Dar es Salaam, Tanzania"),
                ("Telephone:", "+255 714 588 799"),
                ("Mobile:", "+255 714 588 799"),
                ("Email:", "info@flytoday.co.tz")
            ]
            col_widths = [2*inch, 4*inch]
            row_height = line_height * 1.5
            x = margin
            for row in table_data:
                p.line(x, y, x + sum(col_widths), y)
                p.drawString(x + 0.1*inch, y - row_height + 0.1*inch, row[0])
                p.drawString(x + col_widths[0] + 0.1*inch, y - row_height + 0.1*inch, row[1])
                y -= row_height
                p.line(x, y, x + sum(col_widths), y)
            p.line(x, y + row_height * len(table_data), x, y)
            p.line(x + col_widths[0], y + row_height * len(table_data), x + col_widths[0], y)
            p.line(x + sum(col_widths), y + row_height * len(table_data), x + sum(col_widths), y)
            if y < margin:
                p.showPage()
                y = height - margin
            # Page 3
            y -= line_height * 2
            text = "Contact Person & Position in the Organization:"
            p.drawString(margin, y, text)
            y -= line_height
            text = "Our Organization’s Contact personnel for contract executions are as follows;"
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            # Draw contact person table
            table_data = [
                ("Contact Person", "Position in the Organization", "Contact"),
                (obj.contact_person, obj.contact_position, f"Mobile: {obj.contact_mobile}"),
                ("", "", f"Email: {obj.contact_email}")
            ]
            col_widths = [2*inch, 2*inch, 2*inch]
            row_height = line_height * 1.5
            x = margin
            for i, row in enumerate(table_data):
                p.line(x, y, x + sum(col_widths), y)
                for j, cell in enumerate(row):
                    p.drawString(x + sum(col_widths[:j]) + 0.1*inch, y - row_height + 0.1*inch, cell)
                y -= row_height
                p.line(x, y, x + sum(col_widths), y)
                if i == 0:
                    p.setFont("Helvetica-Bold", font_size)
                else:
                    p.setFont("Helvetica", font_size)
            for j in range(len(col_widths) + 1):
                p.line(x + sum(col_widths[:j]), y + row_height * len(table_data), x + sum(col_widths[:j]), y)
            y -= line_height * 2
            text = "Our Bank details are detailed as follows;"
            p.drawString(margin, y, text)
            y -= line_height
            # Draw bank table
            table_data = [
                ("Bank Name:", obj.bank_name),
                ("Branch Name:", obj.branch_name),
                ("Account name:", obj.account_name),
                ("City", obj.city),
                ("Country:", obj.country),
                ("Account Type:", obj.account_type),
                ("Account Number:", obj.account_number),
                ("Swift Code:", obj.swift_code)
            ]
            col_widths = [2*inch, 4*inch]
            row_height = line_height * 1.5
            x = margin
            for row in table_data:
                p.line(x, y, x + sum(col_widths), y)
                p.drawString(x + 0.1*inch, y - row_height + 0.1*inch, row[0])
                p.drawString(x + col_widths[0] + 0.1*inch, y - row_height + 0.1*inch, row[1])
                y -= row_height
                p.line(x, y, x + sum(col_widths), y)
            for j in range(len(col_widths) + 1):
                p.line(x + sum(col_widths[:j]), y + row_height * len(table_data), x + sum(col_widths[:j]), y)
            y -= line_height * 2
            text = "We hope our enclosed proposal meets with your approval and we assure you that if favored with being shortlisted, we shall provide you with the best possible service once invited to tender."
            lines = textwrap.wrap(text, width=70)
            for line in lines:
                p.drawString(margin, y, line)
                y -= line_height
            y -= line_height
            text = "Yours sincerely,"
            p.drawString(margin, y, text)
            y -= line_height
            text = "FLY TODAY TRAVEL COMPANY LIMITED"
            p.drawString(margin, y, text)
            y -= line_height * 2
            text = "AUTHORISED SIGNATORY"
            p.drawString(margin, y, text)
            # Assume no seal image
            if y < margin:
                p.showPage()
                y = height - margin
            # Page 4 if needed, but sample has 4 pages, page 1 blank? But in code, adjust if content overflows
            p.save()
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="cover_letter.pdf"'
            return response
        else:
            queryset = CoverLetter.objects.all()
            serializer = CoverLetterSerializer(queryset, many=True)
            return Response(serializer.data)