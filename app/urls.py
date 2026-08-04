from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Auth
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('signout/', views.logout_view, name='signout'),

    # Master Data & User Management (Sections, Suppliers, Users)
    path('sections/', views.sections_list_view, name='sections_list'),
    path('suppliers/', views.suppliers_list_view, name='suppliers_list'),
    path('users/', views.manage_users_view, name='manage_users'),

    # Real-Time Inventory & Optimization
    path('medications/', views.medications_list_view, name='medications_list'),
    path('medications/add/', views.add_medication_view, name='add_medication'),

    # Goods Receipt Intake & Physical Stock Auditing
    path('inventory/receive/', views.receive_batch_view, name='receive_batch'),
    path('inventory/api/medication-stock/<int:medication_id>/', views.medication_stock_api, name='medication_stock_api'),
    path('inventory/adjust/', views.stock_adjustment_view, name='stock_adjustment'),

    # FR3 & FR4 Purchase Orders & Auto Draft PO
    path('orders/', views.purchase_orders_view, name='purchase_orders'),
    path('orders/auto-po/<int:medication_id>/', views.auto_generate_draft_po_view, name='auto_generate_draft_po'),
    path('orders/approve/<int:po_id>/', views.approve_po_view, name='approve_po'),

    # FR6 ABC Classification Console
    path('analytics/abc/', views.abc_classification_view, name='abc_classification'),

    # FR7 FEFO Expiries Monitoring & Quarantine
    path('inventory/expiries/', views.expiries_monitoring_view, name='expiries_monitoring'),
    path('inventory/quarantine/<int:batch_id>/', views.quarantine_batch_view, name='quarantine_batch'),

    # FR2 Immutable Audit Ledger
    path('audit/ledger/', views.stock_audit_ledger_view, name='stock_audit_ledger'),

    # FR9 Reports & Export Module
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/', views.export_report_csv, name='export_report_csv'),
]
