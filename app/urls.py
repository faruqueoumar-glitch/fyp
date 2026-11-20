from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Auth
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('founder/', views.founder_dashboard_view, name='founder_dashboard'),
    path('founder/users/', views.founder_users_view, name='founder_users'),
    path('help/', views.help_view, name='help'),
    path('login/', views.login_view, name='login'),
    path('signout/', views.logout_view, name='signout'),
    path('register/', views.register_view, name='register'),

    # Password Reset URLs (self-service, multi-tenant safe)
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('password-reset/done/', views.password_reset_done_view, name='password_reset_done'),

    # Lightweight health check (DB-free) for uptime pingers & cold-start retry
    path('healthz/', views.healthz_view, name='healthz'),

    # Service Worker and Manifest ( served with correct content types )
    path('sw.js', views.sw_js, name='sw_js'),
    path('manifest.json', views.manifest_json, name='manifest_json'),

    # Offline fallback page
    path('offline/', views.offline_view, name='offline'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('reset/done/', views.password_reset_complete_view, name='password_reset_complete'),

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

    # FEFO Dispense & Point of Sale (POS) Cart System
    path('dispense/', views.fefo_dispense_view, name='fefo_dispense'),
    path('dispense/cart/add/', views.cart_add_item, name='cart_add_item'),
    path('dispense/cart/update/', views.cart_update_item, name='cart_update_item'),
    path('dispense/cart/remove/', views.cart_remove_item, name='cart_remove_item'),
    path('dispense/cart/contents/', views.cart_get_contents, name='cart_get_contents'),
    path('dispense/cart/clear/', views.cart_clear, name='cart_clear'),
    path('dispense/checkout/', views.checkout_and_dispense, name='checkout_and_dispense'),
    path('dispense/receipt/<str:transaction_ref>/', views.sales_receipt_view, name='sales_receipt'),
    path('dispense/history/', views.sales_history_view, name='sales_history'),

    # FR3 & FR4 Purchase Orders & Auto Draft PO
    path('orders/', views.purchase_orders_view, name='purchase_orders'),
    path('orders/auto-po/<int:medication_id>/', views.auto_generate_draft_po_view, name='auto_generate_draft_po'),
    path('orders/approve/<int:po_id>/', views.approve_po_view, name='approve_po'),
    path('pharmacy/load-sample-data/', views.load_sample_data, name='load_sample_data'),
    path('pharmacy/clear-sample-data/', views.clear_sample_data, name='clear_sample_data'),

    # FR6 ABC Classification Console
    path('analytics/abc/', views.abc_classification_view, name='abc_classification'),

    # FR7 FEFO Expiries Monitoring & Quarantine
    path('inventory/expiries/', views.expiries_monitoring_view, name='expiries_monitoring'),
    path('inventory/quarantine/<int:batch_id>/', views.quarantine_batch_view, name='quarantine_batch'),

    # FR2 Immutable Audit Ledger
    path('audit/ledger/', views.stock_audit_ledger_view, name='stock_audit_ledger'),
    path('audit/controlled-register/', views.controlled_register_view, name='controlled_register'),
    path('sections/medication/<int:med_id>/schedule/', views.medication_schedule_update_view, name='medication_schedule_update'),

    # FR9 Reports & Export Module
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/', views.export_report_csv, name='export_report_csv'),
    # Identity, Staff/Admin ID Card & Branch Branding
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/id-card/', views.staff_id_card, name='staff_id_card'),
    path('branch/settings/', views.branch_settings, name='branch_settings'),
]
