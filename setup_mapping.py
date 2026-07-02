import json
import re

business_tables = [
    "Patient", "Visit", "BillingDetails", "OrderDtl", "Receipt_Dtls", 
    "DrugSaleDtl", "WD_Prescription_Details", 
    "WD_PrescriptionDaysFrequency", "Ds_PatientAppoinment", "Ds_PatientAppoinmentTemperary", 
    "LABTestParam", "LABTestResult", "OT_SCHEDULLING_DTL", 
    "WD_TPRBP_DTLS", "Ctpl_OpInitialAssessment", "Ctpl_OPNurseAssessment_Dtl",
    "OrderMst", "Receipt_Mst", "Billing_Mst", "DrugSaleMst", "WD_Prescription_Mst", "OT_Scheduling_Mst"
]

raw_data = """
"WITHINDAYS", "WithinDays_Mst", "	true"
"WARDS", "Ward_Mst   where ISNULL(Deactive,0)=0", "	true"
"UNIT", "UnitMst", "	true"
"SCIENTIFICABSENCEREASONS", "NPhiesScientificAbscReasons  ", "	true"
"ROUTE", "Route_Mst", "	true"
"RESULT", "Result_Mst", "	true"
"PROBLEM", "CTpl_CheckBoxCategoryDetails where SubModID=1145 and CategoryID=1 and isnull(Deactive,0)=0", "	true"
"PERIOD", "Period_Mst", "	true"
"PAINSCORE", "PainScore_Mst", "	true"
"PAINASSESSMENTTOOL", "PainAssementTools", "	true"
"OUTTAKEITEM", "OutputItem_Mst", "	true"
"OUTPUTITEM", "OutputItem_Mst   where ISNULL(Deactive,0)=0", "	true"
"ORADMISSIONTYPE", "DDAdmissionType", "	true"
"ONSET", "NphiesOnsetConditionType ORDER BY 1 ASC", "	true"
"NATIONALITY", "Nationality_Master", "	true"
"METHODOFDELIVERY", "MethodOfDelivery_Mst", "	true"
"LASTDURATION", "LastDuration_Mst", "	true"
"INTAKEITEM", "IntakeItem_Mst", "	true"
"GETTPAAGREMENTTYPEMST", "TPAAgreementType_mst where Deactive=0  ORDER BY AgreementTypeId", "	true"
"GETSWIPEMACHINE", "SwapMachine_Mst WHERE ISNULL(Deactive,0) = 0", "	true"
"GETSERVICESPACKAGETYPE", "ServicesPackageType", "	true"
"GETSBAGREEMENT", "TPAAgreementType_mst where Deactive = 0", "	true"
"GETROUTINESTAT", "ROUTINE_STAT_MST", "	true"
"GETRELIGION", "Religion_Mst where Deactive=0  ORDER BY Religion_ID", "	true"
"GETRELATIONSHIP", "Relation_Mst ORDER BY Relation_ID ASC", "	true"
"GETPRPATIENTINSURANCEID", "Insurance_Mst where ISnull(Deactive,0)=0", "	true"
"GETPAYMENTMODE", "paymentmode_mst where Deactive=0", "	true"
"GETPATIENTTYPE", "patienttype_mst", "	true"
"GETPATIENTSUBTYPE", "PatientSubType_Mst", "	true"
"GETPATIENTIDTYPE", "PatientIdType_mst", "	true"
"GETOTREFRALTYPE", "DDRefreralType", "	true"
"GETOCCUPATION", "Occupation_Mst  where isnull(Deactive,0)=0", "	true"
"GETNSTATUS", "NphiesRequestStatus_mst", "	true"
"GETNPPAYEE", "Payee_Mst WHERE (Deactive = 0) And PayeeID <> 1", "	true"
"GETNPINVESTIGATION", "NPhiesInvestigationResults where isnull(Deactive,0) = 0", "	true"
"GETNATIONALITY", " Nationality_master WHERE isnull(DeActive,0)=0 order by NationalityDesc", "	true"
"GETMARITALSTATUS", "MaritalStatus_mst where Deactive= 0", "	true"
"GETLIVINGMST", "Living_Mst", "	true"
"GETINSURANCEAPPROVALTYPE", "InsuranceApprovalType", "	true"
"GETINFO", "WD_PrescriptionInfo", "	true"
"GETGENDERMST", "Gender_Mst WHERE Active = 1 ORDER BY 1 ASC", "	true"
"GETGENDER", "Gender_Mst Where Active=1", "	true"
"GETERADMITSOURCE", "NPhiesAdmitSource", "	true"
"GETCITY", "City_Mst Where Isnull(Deactive,0)=0", "	true"
"GETCHIEFCOMPLIANTMST", "ChiefComplaintMst where Description like %filter%", "	true"
"GETCHIEFCOMPLAINTMST", " ChiefComplaintMst where Description  like '%filter%'", "	true"
"GETCASETYPE", "CaseType_Mst Where IsNull(Deactive,0) = 0 and VisitTypeID=2", "	true"
"GETBANKNAME", "Bank_Mst where Deactive = 0", "	true"
"GETAPPROVESTATUS", "TPAApprovalStatus_Mst where isnull(Deactive,0) = 0", "	true"
"GETADMISSIONSOURCETYPE", "AdmissionSource", "	true"
"GET)Insert INTO Generic_Mst ([case],sqlStr)VALUES(TYPE", ")Insert INTO Generic_Mst ([case],sqlStr)VALUES(Type_Mst Where IsNull(Deactive,0) = 0 and VisitTypeID=2", "	true"
"FREQUENCYDAYS", "WD_PrescriptionDaysFrequency", "	true"
"FREQUENCY", "WD_PrescriptionFrequency", "	true"
"EVALUATION", "CTpl_CheckBoxCategoryDetails where SubModID=1145 and CategoryID=2 and isnull(Deactive,0)=0", "	true"
"DISCOUNTREASONMST", "DiscountReason_Mst where isnull(deactive,0)= 0", "	true"
"DISCOUNTAUTHORITY", "vwDiscountAuthority", "	true"
"DISCHARGETYPE", "DischargeType_Mst where (Deactive = 0 or Deactive is null) ORDER BY DischargeType_ID ASC", "	true"
"DISCHARGETO", "DischargeTo_Mst", "	true"
"DIAGNOSISTYPE", "NphiesDiagnosisTypeID ORDER BY 1 ASC", "	true"
"CARETYPE", "CareType_mst", "	true"
"CANCELREASON", "Reason_Mst Where ReasonTypeId=10 AND Deactive=0", "	true"
"ALLERGYTYPE", "Allergies_mst", "	true"
"ALLERGYMEDICINE", "AllergyMedicineMst WHERE Deactive =0", "	true"
"ALLERGYFOOD", "AllergyFoodMst WHERE Deactive = 0", "	true"
"USERMST", "User_Mst", "	true"
"VISITTYPEMST", "VisitType_Mst", "	true"
"SERVICEMST", "Service_Mst", "	true"
"ROOMMST", "Room_Mst", "	true"
"BEDMST", "Bed_Mst", "	true"
"FLOORMST", "Floor_Mst", "	true"
"BLOCKMST", "Block_Mst", "	true"
"BEDSTATUSMST", "Bed_Status_Mst", "	true"
"IVITEM", "IVItem", "	true"
"LABTEST", "LABTest", "	true"
"""

master_tables = []
for line in raw_data.strip().split('\n'):
    if not line.strip(): continue
    parts = line.split('", "')
    if len(parts) >= 2:
        code_name = parts[0].strip('"')
        sql_part = parts[1].strip('"')
        
        # separate table name from filter
        table_name = sql_part
        filter_str = None
        
        # Regex to find WHERE or ORDER BY
        match = re.search(r'\s+(where|WHERE|order by|ORDER BY)\s+(.*)', sql_part)
        if match:
            table_name = sql_part[:match.start()].strip()
            # If it's just ORDER BY, maybe we don't need it as a WHERE filter, but let's capture the whole condition just in case, or we can just capture the WHERE part.
            if match.group(1).lower() == 'where':
                filter_str = sql_part[match.start():].strip()
        
        # Special case cleanup
        if table_name.startswith(')Insert'):
             continue # skipping the malformed generic line

        system_uri = f"http://hospital/fhir/{table_name.lower().replace('_mst', '').replace('_master', '')}"

        master_tables.append({
            "source_table": table_name.strip(),
            "source_filter": filter_str,
            "id_column": "ID",
            "code_column": "Code",
            "display_column": "Description",
            "display_arb_column": "DescriptionArb",
            "active_column": "Deactive",
            "system_uri": system_uri
        })

mapping = {
    "business_tables": business_tables,
    "master_tables": master_tables
}

with open("config/mapping.json", "w") as f:
    json.dump(mapping, f, indent=4)
print("Mapping generated successfully.")
