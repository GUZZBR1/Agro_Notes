<?php

declare(strict_types=1);

namespace Drupal\farm_quick\Hook;

use Drupal\Component\Utility\Html;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Routing\RouteMatchInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_quick\QuickFormInstanceManagerInterface;

/**
 * Help hook implementations for farm_quick.
 */
class HelpHooks {

  use StringTranslationTrait;

  public function __construct(
    protected QuickFormInstanceManagerInterface $quickFormInstanceManager,
  ) {}

  /**
   * Implements hook_help().
   */
  #[Hook('help')]
  public function help($route_name, RouteMatchInterface $route_match) {
    $output = '';

    // Quick forms index help text.
    if ($route_name == 'farm.quick') {
      $output .= '<p>' . $this->t('Quick forms make it easy to record common activities.') . '</p>';
    }

    // Load help text for individual quick forms.
    if (strpos($route_name, 'farm.quick.') === 0) {
      $quick_form_id = $route_match->getParameter('id');
      if ($route_name == 'farm.quick.' . $quick_form_id) {
        $quick_form = $this->quickFormInstanceManager->getInstance($quick_form_id);
        $output = [
          '#type' => 'html_tag',
          '#tag' => 'p',
          '#value' => Html::escape($quick_form->getHelpText()),
          '#cache' => [
            'tags' => $quick_form->getCacheTags(),
          ],
        ];
      }
    }

    return $output;
  }

}
