<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views\Hook;

use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_flag\FarmFlagHelper;
use Drupal\farm_ui_views\FarmUiViewsHelper;

/**
 * Form hook implementations for farm_ui_views.
 */
class FormHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_form_BASE_FORM_ID_alter().
   */
  #[Hook('form_views_exposed_form_alter')]
  public function formViewsExposedFormAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Load form state storage and bail if the View is not stored.
    $storage = $form_state->getStorage();
    if (empty($storage['view'])) {
      return;
    }

    /** @var \Drupal\views\ViewExecutable $view */
    $view = $storage['view'];

    // Check if the view display has the collapsible_filter extender enabled.
    $extenders = $view->getDisplay()->getExtenders();
    if (array_key_exists('collapsible_filter', $extenders) && $extenders['collapsible_filter']->options['collapsible']) {

      // Render filters in collapsible details element.
      // Only open the filters if a non-default filter value is provided.
      // This is needed to prevent the filter from opening when click sort is
      // applied and all default filter values are passed as query parameters.
      $open_input = FALSE;
      foreach ($view->getExposedInput() as $filter_name => $filter_value) {
        /**
         * @var string $filter_name
         * @var string|array $filter_value
         */

        // Check if the exposed input is for a filter.
        if (isset($view->filter[$filter_name])) {

          // Get the default filter value.
          $default_filter_value = $view->filter[$filter_name]->value;

          // If the default is an array with one value and a single string value
          // is provided in input, consider the default filter to be a string
          // instead of an array. This fixes the status filter.
          if (is_array($default_filter_value) && count($default_filter_value) == 1 && !is_array($filter_value)) {
            $default_filter_value = reset($default_filter_value);
          }

          // Open the filters if the filter value does not equal the default.
          if ($filter_value != $default_filter_value) {
            $open_input = TRUE;
            break;
          }
        }
      }
      $form['#theme_wrappers']['details'] = [
        '#title' => $this->t('Filter'),
        '#attributes' => [

          // Open if there is exposed input.
          'open' => $open_input,
        ],
        '#summary_attributes' => [],
      ];
      $form['#attached']['library'][] = 'farm_ui_views/views_collapsible_filter';
    }

    // We only want to alter the Views we provide.
    if (!in_array($storage['view']->id(), ['farm_asset', 'farm_log', 'farm_plan'])) {
      return;
    }

    // If there is no exposed filter for flags, bail.
    if (empty($form['flag_value'])) {
      return;
    }

    // Get the entity type and (maybe) bundle.
    $entity_type = $storage['view']->getBaseEntityType()->id();
    $bundle = FarmUiViewsHelper::getBundleArgument($storage['view'], $storage['display']['id'], $storage['view']->args);
    $bundles = !empty($bundle) ? [$bundle] : [];
    $allowed_options = FarmFlagHelper::flagOptions($entity_type, $bundles, TRUE);
    $form['flag_value']['#options'] = $allowed_options;
  }

}
