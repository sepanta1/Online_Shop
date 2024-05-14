from django.contrib import admin
from .models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User

# Register the model on the admin section thing
admin.site.register(ShippingAddress)
admin.site.register(Order)
admin.site.register(OrderItem)


# Create an OrderItem inline
class OrderItemInline(admin.StackedInline):
    model = OrderItem
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    model = Order
    readonly_fields = ['date_ordered']
    inlines = [OrderItemInline]


admin.site.unregister(Order)
admin.site.register(Order, OrderAdmin)
