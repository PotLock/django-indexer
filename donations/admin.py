from django.contrib import admin
from django.utils.dateformat import format
from django.utils.timezone import localtime
from .models import Donation

class DonationAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Donation._meta.get_fields() if field.name != 'id']
    list_display.extend(['donor_address', 'recipient_address', 'ft_address', 'referrer_address', 'chef_address'])  # Add custom methods for addresses
    search_fields = ('message', 'donor__address')  # You can add more fields here
    list_filter = ('donated_at', 'donor', 'pot')  # Added default filters, you can add custom DateRangeFilter
    date_hierarchy = 'donated_at'
    ordering = ('-donated_at',)

    def donor_address(self, obj):
        return obj.donor.id
    donor_address.admin_order_field = 'donor__address'  # Allows column order sorting
    donor_address.short_description = 'Donor Address'

    def recipient_address(self, obj):
        return obj.recipient.id if obj.recipient else None

    def ft_address(self, obj):
        return obj.ft.id

    def referrer_address(self, obj):
        return obj.referrer.id if obj.referrer else None

    def chef_address(self, obj):
        return obj.chef.id if obj.chef else None

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super(DonationAdmin, self).formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in ['donated_at']:  # Add more fields if needed
            field.widget.format = '%d-%m-%Y %H:%M'  # Change to your preferred format
            field.widget.attrs.update({'class': 'vDateField', 'size': '20'})
        return field

admin.site.register(Donation, DonationAdmin)
