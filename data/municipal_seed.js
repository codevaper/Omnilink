

db.permit_applications.drop();

db.permit_applications.insertMany([
  {
    permit_id: "MUN2024001",
    applicant_fname: "Priya",
    applicant_lname: "Sharma",
    father_name: "Raj Kumar Sharma",
    address_line_1: "123 Gandhi Road, Sector 15",
    contact_number: "9876543210",
    permit_type: "building_permit",
    application_date: new Date("2024-01-15"),
    annual_income: 25000,
    pan_number: "ABCDE1234F",
    status: "pending"
  },
  {
    permit_id: "MUN2024002",
    applicant_fname: "Amit",
    applicant_lname: "Patel",
    father_name: "Vijay Kumar Patel",
    address_line_1: "456 Nehru Street, Block B",
    contact_number: "9876543211",
    permit_type: "water_connection",
    application_date: new Date("2024-01-16"),
    annual_income: 30000,
    pan_number: "FGHIJ5678K",
    status: "approved"
  },
  {
    permit_id: "MUN2024003",
    applicant_fname: "Sunita",
    applicant_lname: "Singh",
    father_name: "Ram Bahadur Singh",
    address_line_1: "789 MG Road, Phase 2",
    contact_number: "9876543212",
    permit_type: "trade_license",
    application_date: new Date("2024-01-17"),
    annual_income: 22000,
    pan_number: "LMNOP9012Q",
    status: "processing"
  },
  {
    permit_id: "MUN2024004",
    applicant_fname: "Rajesh",
    applicant_lname: "Kumar",
    father_name: "Mohan Lal Kumar",
    address_line_1: "321 Park Avenue, Zone A",
    contact_number: "9876543213",
    permit_type: "construction_permit",
    application_date: new Date("2024-01-18"),
    annual_income: 35000,
    pan_number: "RSTUV3456W",
    status: "pending"
  },
  {
    permit_id: "MUN2024005",
    applicant_fname: "Meera",
    applicant_lname: "Gupta",
    father_name: "Anil Gupta",
    address_line_1: "654 Lake View, Sector 8",
    contact_number: "9876543214",
    permit_type: "shop_license",
    application_date: new Date("2024-01-19"),
    annual_income: 28000,
    pan_number: "XYZAB7890C",
    status: "approved"
  }
]);


