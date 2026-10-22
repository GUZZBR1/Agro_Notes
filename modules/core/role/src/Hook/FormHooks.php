<?php

declare(strict_types=1);

namespace Drupal\farm_role\Hook;

use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_role\ManagedRolePermissionsManagerInterface;
use Drupal\user\PermissionHandlerInterface;

/**
 * Form hook implementations for farm_role.
 */
class FormHooks {

  use StringTranslationTrait;

  public function __construct(
    protected PermissionHandlerInterface $permissionHandler,
    protected ManagedRolePermissionsManagerInterface $managedRolePermissionsManager,
  ) {}

  /**
   * Implements hook_form_BASE_FORM_ID_alter().
   */
  #[Hook('form_user_admin_permissions_alter')]
  public function formUserAdminPermissionsAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Attach managed role CSS.
    $form['#attached']['library'][] = 'farm_role/managed_role';

    // Save a list of managed role IDs keyed by their index in the form.
    $managed_roles = $this->managedRolePermissionsManager->getMangedRoles();
    $managed_roles_indices = array_intersect(
      array_keys($form['role_names']['#value']),
      array_keys($managed_roles)
    );

    // Append '(managed)' to managed role labels in the table header.
    foreach ($managed_roles_indices as $index => $role) {

      // Offset by 1 for the first table column.
      $offset = $index + 1;

      // Build new label.
      $label = $form['permissions']['#header'][$offset]['data'];
      $new = $label . ' (' . $this->t('managed') . ')';

      // Set new label.
      $form['permissions']['#header'][$offset]['data'] = $new;
    }

    // Get a list of permissions.
    $permissions = $this->permissionHandler->getPermissions();
    $permission_names = array_keys($permissions);

    // Iterate over each permission in the form.
    foreach ($form['permissions'] as $name => $permission) {

      // Only check permission arrays, skip high level form and wrapper
      // elements.
      if (in_array($name, $permission_names)) {

        // Iterate over each role under the permission.
        foreach (array_keys($permission) as $rid) {

          // Disable the checkbox for all managed roles.
          if (in_array($rid, $managed_roles_indices)) {
            $form['permissions'][$name][$rid]['#disabled'] = TRUE;

            // If the permission is enabled on the role, add CSS class.
            if ($this->managedRolePermissionsManager->isPermissionInRole($name, $managed_roles[$rid])) {
              $form['permissions'][$name][$rid]['#attributes']['class'][] = 'managed';
            }
          }
        }
      }
    }
  }

}
