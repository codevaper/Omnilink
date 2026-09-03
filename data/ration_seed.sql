DROP TABLE IF EXISTS ration_crds;

CREATE TABLE ration_crds (
    id SERIAL PRIMARY KEY,
    f_nme VARCHAR(100),
    l_nme VARCHAR(100),
    fth_nme VARCHAR(100),
    adr_ln1 VARCHAR(200),
    ph_no VARCHAR(15),
    crd_no VARCHAR(20) UNIQUE,
    fml_sz INTEGER,
    inc_amt DECIMAL(10, 2),
    created_dt TIMESTAMP DEFAULT NOW(),
    pan_no VARCHAR(10)
);

INSERT INTO
    ration_crds (
        f_nme,
        l_nme,
        fth_nme,
        adr_ln1,
        ph_no,
        crd_no,
        fml_sz,
        inc_amt,
        pan_no
    )
VALUES (
        'Priya',
        'Sharma',
        'Raj Kumar Sharma',
        '123 Gandhi Road, Sector 15',
        '9876543210',
        'RC2024001',
        4,
        25000.00,
        'ABCDE1234F'
    ),
    (
        'Amit',
        'Patel',
        'Vijay Kumar Patel',
        '456 Nehru Street, Block B',
        '9876543211',
        'RC2024002',
        3,
        30000.00,
        'FGHIJ5678K'
    ),
    (
        'Sunita',
        'Singh',
        'Ram Bahadur Singh',
        '789 MG Road, Phase 2',
        '9876543212',
        'RC2024003',
        5,
        22000.00,
        'LMNOP9012Q'
    ),
    (
        'Rajesh',
        'Kumar',
        'Mohan Lal Kumar',
        '321 Park Avenue, Zone A',
        '9876543213',
        'RC2024004',
        2,
        35000.00,
        'RSTUV3456W'
    ),
    (
        'Meera',
        'Gupta',
        'Anil Gupta',
        '654 Lake View, Sector 8',
        '9876543214',
        'RC2024005',
        3,
        28000.00,
        'XYZAB7890C'
    );